from src.db import sessionLocal
from src.models import Plan

db = sessionLocal()

plans = [
    Plan(
        name="Free",
        api_call_quota=100,
        monthly_price_cents=0,
    ),
    Plan(
        name="Pro",
        api_call_quota=1000,
        monthly_price_cents=2900,
    ),
]

db.add_all(plans)
db.commit()
db.close()

print("Plans seeded")