# main.py
from datetime import datetime
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
from sqlalchemy import select

from .models import Tenant, Plan, Subscription
from .schemas import TenantCreate, UsageRequest

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


@app.post("/tenants")
def create_tenant(request: TenantCreate, db: Session = Depends(get_db),):
    free_plan = db.scalar(
        select(Plan).where(Plan.name == "Free")
    )

    if not free_plan:
        raise HTTPException(
            status_code=500,
            detail="Free plan not found",
        )

    tenant = Tenant(name=request.name)

    db.add(tenant)
    db.flush()

    subscription = Subscription(tenant_id=tenant.id,plan_id=free_plan.id,status="active")

    db.add(subscription)
    db.commit()
    db.refresh(tenant)

    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
        "plan": "Free",
        "subscription_status": "active",
    }


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

    subscription = meter.get_subscription(tenant_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    plan = meter.get_plan(subscription)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")


    api_cost = (api_calls or 0) * 0.001  
    ai_cost = 0

    start_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    ai_cost = (ai_tokens or 0) * 0.003
    return {
         "tenant_id": tenant_id,
        "period": "current_month",
        "plan": {
            "name": plan.name,
            "api_call_limit": plan.api_call_quota,
            "monthly_price_cents": plan.monthly_price_cents,
        },
        "usage": {
            "api_calls": {
                "used": api_calls,
                "limit": plan.api_call_quota,
                "cost_cents": int(api_cost * 100),  # Convert to cents
            },
            "ai_tokens": {
                "used": ai_tokens,
                "cost_cents": int(ai_cost * 100),  # Convert to cents
            },
        },
        "total_cost_cents": int((api_cost + ai_cost) * 100),
    }
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook")

    # Deduplication
    existing = db.scalar(
        select(StripeEvent).where(StripeEvent.stripe_event_id == event["id"])
    )
    if existing:
        return {"status": "already_processed"}

    # Store event for deduplication
    db.add(StripeEvent(stripe_event_id=event["id"]))
    db.flush()

    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
  
        session_dict = session.to_dict()
        metadata = session_dict.get("metadata", {})
        
        # Check if this is a test event without metadata
        if not metadata:
            db.commit()
            return {"status": "ignored_test_event"}
        
        tenant_id = metadata.get("tenant_id")
        plan_id = metadata.get("plan_id")
        
        if not tenant_id or not plan_id:
            db.commit()
            return {"status": "ignored_incomplete_metadata"}
        
        tenant_id = int(tenant_id)
        plan_id = int(plan_id)
        
        # Update subscription
        subscription = db.scalar(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
        )
        
        if subscription:
            subscription.plan_id = plan_id
            subscription.status = "active"
            subscription.stripe_customer_id = session_dict.get("customer")
            subscription.stripe_subscription_id = session_dict.get("subscription")
            
            db.commit()
            return {"status": "subscription_updated"}
        
        db.commit()
        return {"status": "no_subscription_found"}

    # Handle customer.subscription.updated
    elif event["type"] == "customer.subscription.updated":
        stripe_sub = event["data"]["object"]
        stripe_sub_dict = stripe_sub.to_dict()  
        subscription = db.scalar(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_dict.get("id")
            )
        )
        
        if subscription:
            stripe_status = stripe_sub_dict.get("status")
            status_map = {
                "active": "active",
                "past_due": "past_due",
                "unpaid": "past_due",
                "canceled": "canceled",
                "incomplete": "inactive",
            }
            subscription.status = status_map.get(stripe_status, "inactive")
            
            if stripe_status == "canceled":
                free_plan = db.scalar(select(Plan).where(Plan.name == "Free"))
                if free_plan:
                    subscription.plan_id = free_plan.id
            
            db.commit()
            return {"status": "subscription_updated"}
        
        return {"status": "subscription_not_found"}

    # Handle customer.subscription.deleted
    elif event["type"] == "customer.subscription.deleted":
        stripe_sub = event["data"]["object"]
        stripe_sub_dict = stripe_sub.to_dict()  # ✅ Convert to dict
        
        subscription = db.scalar(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_dict.get("id")
            )
        )
        
        if subscription:
            subscription.status = "canceled"
            free_plan = db.scalar(select(Plan).where(Plan.name == "Free"))
            if free_plan:
                subscription.plan_id = free_plan.id
            
            db.commit()
            return {"status": "subscription_canceled"}
        
        return {"status": "subscription_not_found"}

    # Ignore other event types
    db.commit()
    return {"status": f"ignored_event_{event['type']}"}



@app.post("/tenants/{tenant_id}/billing/checkout")
def checkout(tenant_id: int, request: CheckoutRequest, db: Session = Depends(get_db)):
    # Verify tenant exists
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify plan exists
    plan = db.get(Plan, request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    session = create_checkout_session(tenant_id=tenant_id,plan_id=request.plan_id, price_id=request.price_id)

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }



@app.post("/tenants/{tenant_id}/billing/checkout")
def create_checkout(
    tenant_id: int,
    request: CheckoutRequest,  # { plan_id: int, price_id: str }
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout session for subscription upgrade"""
    
    # Verify tenant exists
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify plan exists
    plan = db.get(Plan, request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Create Stripe Checkout session
    try:
        session = create_checkout_session(
            tenant_id=tenant_id,
            plan_id=request.plan_id,
            price_id=request.price_id,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }




# Dummy endpoint
class GenerateRequest(BaseModel):
    prompt: str
    idempotency_key: str
    
class GenerateResponse(BaseModel):
    usage_event_id: int
    tokens_used: int
    cost_cents: int
    quota_remaining: int
    response: str

@app.post("/tenants/{tenant_id}/generate")
def generate_ai_response(
    tenant_id: int,
    request: GenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Dummy endpoint that simulates AI generation.
    Records usage for AI tokens and enforces quotas.
    """
    meter = MeterService(db)
    
    # Simulate token usage (random between 100-5000 tokens)
    import random
    tokens_used = random.randint(100, 5000)
    
    try:

        event = meter.record(
            tenant_id=tenant_id,
            usage_type="ai_token",
            quantity=tokens_used,
            idempotency_key=request.idempotency_key
        )
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get current usage to show remaining quota
    subscription = meter.get_subscription(tenant_id)
    plan = meter.get_plan(subscription)
    current_usage = meter.get_monthly_usage(tenant_id, "ai_token")
    
    # Calculate cost (simplified - would need token breakdown in production)
    cost_cents = int(tokens_used * 0.003 * 100)  # $0.003 per token * 100 cents
    
    # Simulated AI response
    response_text = f"Generated response for: {request.prompt[:50]}..."
    
    return GenerateResponse(
        usage_event_id=event.id,
        tokens_used=tokens_used,
        cost_cents=cost_cents,
        quota_remaining=plan.api_call_quota - current_usage if current_usage else plan.api_call_quota,
        response=response_text
    )