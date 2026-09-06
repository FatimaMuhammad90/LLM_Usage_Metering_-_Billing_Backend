import os
import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_checkout_session(tenant_id: int, plan_id: int, price_id: str):
    
    return stripe.checkout.Session.create(mode="subscription", line_items=[
    {
        "price": price_id,
        "quantity": 1,
    }],
    success_url="http://localhost:8000/billing/success",
    cancel_url="http://localhost:8000/billing/cancel",

    metadata={
            "tenant_id": str(tenant_id),
            "plan_id": str(plan_id),
        },
    )