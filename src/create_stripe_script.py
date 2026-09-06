# create_stripe_price.py
import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# This creates both product AND price in one go
price = stripe.Price.create(
    product_data={"name": "Pro Plan"},
    unit_amount=2900,  # $29.00 in cents
    currency="usd",
    recurring={"interval": "month"},
)

print(f"\nYour Price ID is: {price.id}")
print(f"Copy this and use it in your checkout requests")
print(f"Example: curl -X POST ... -d '{{\"plan_id\": 2, \"price_id\": \"{price.id}\"}}'")