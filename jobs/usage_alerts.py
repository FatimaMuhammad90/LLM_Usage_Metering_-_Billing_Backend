import os
from datetime import datetime
from sqlalchemy import select

from src.db import sessionLocal
from src.models import Subscription, Plan
from src.services import MeterService


def check_usage_alerts():

    db = sessionLocal()
        
    try:
        # Get all active subscriptions
        subscriptions = db.scalars(select(Subscription).where(Subscription.status == "active")).all()
        
        if not subscriptions:
            print("No active subscriptions found.")
            return []

        alerts = []
        
        for sub in subscriptions:
            meter = MeterService(db)
        
            usage = meter.get_monthly_usage(sub.tenant_id, "api_call") or 0

            plan = meter.get_plan(sub)
            if not plan:
                continue
            
            limit = plan.api_call_quota
            if limit == 0:
                continue

            percentage = (usage / limit) * 100
            
            # Check thresholds
            if percentage >= 100:
                alerts.append({ "tenant_id": sub.tenant_id, "level": "CRITICAL",  "usage": usage, "limit": limit,  "percentage": 100, "message": f"QUOTA EXCEEDED: {usage}/{limit} API calls"})
                
            elif percentage >= 80:
                alerts.append({ "tenant_id": sub.tenant_id, "level": "WARNING","usage": usage, "limit": limit,"percentage": round(percentage, 1),"message": f"At {round(percentage, 1)}% of quota ({usage}/{limit} API calls)" })
        
        # Log alerts
        if alerts:
            print(f"\n{'='*50}")
            print(f"USAGE ALERTS - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            for alert in alerts:
                print(f"[{alert['level']}] Tenant {alert['tenant_id']}: {alert['message']}")
            print(f"{'='*50}\n")
        else:
            print(f"All tenants within quota - no alerts at {datetime.utcnow()}")
        
        return alerts
        
    finally:
        db.close()

if __name__ == "__main__":
    check_usage_alerts()