from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from .schemas import UsageRequest
from .services import MeterService
from .db import sessionLocal
from .models import StripeEvent, Subscription
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

import os
import stripe
from stripe import error as StripeError
from dotenv import load_dotenv
from fastapi import Request

from .stripe_service import create_checkout_session

load_dotenv()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

app = FastAPI()


class CheckoutRequest(BaseModel):
    plan_id: int
    price_id: str

def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Metering service is running"}


@app.post("/tenants/{tenant_id}/usage")
def record_usage(tenant_id: int,request: UsageRequest, db: Session = Depends(get_db)):

    meter = MeterService(db)
    try:
        event = meter.record(tenant_id=tenant_id, usage_type=request.usage_type, quantity=request.quantity, idempotency_key=request.idempotency_key)

    except PermissionError as e:
        raise HTTPException( status_code=429, detail=str(e))

    
    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "usage_type": event.usage_type,
        "quantity": event.quantity,
        "idempotency_key": event.idempotency_key,
    }


# monthly usage 
@app.get("/tenants/{tenant_id}/usage")
def get_usage(tenant_id: int, db: Session = Depends(get_db)):
    meter = MeterService(db)

    api_calls = meter.get_monthly_usage(tenant_id, "api_call")

    ai_tokens = meter.get_monthly_usage(tenant_id,"ai_token")

    return {
        "tenant_id": tenant_id,
        "period": "current_month",
        "usage": {
            "api_calls": api_calls,
            "ai_tokens": ai_tokens,
        },
    }


@app.post("/tenants/{tenant_id}/billing/checkout")
def checkout(tenant_id: int, request: CheckoutRequest):
    session = create_checkout_session(
        tenant_id=tenant_id,
        plan_id=request.plan_id,
        price_id=request.price_id,
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()

    signature = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook")

    existing = db.scalar(
        select(StripeEvent).where(
            StripeEvent.stripe_event_id == event["id"]
        )
    )

    if existing:
        return {"status": "already_processed"}

    db.add(
        StripeEvent(
            stripe_event_id=event["id"],
        )
    )

    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]

        tenant_id = int(session["metadata"]["tenant_id"])
        plan_id = int(session["metadata"]["plan_id"])

        subscription = db.scalar(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id
            )
        )

        if subscription:
            subscription.plan_id = plan_id
            subscription.status = "active"
            subscription.stripe_customer_id = session.get(
                "customer"
            )
            subscription.stripe_subscription_id = session.get(
                "subscription"
            )

    db.commit()

    return {"status": "processed"}