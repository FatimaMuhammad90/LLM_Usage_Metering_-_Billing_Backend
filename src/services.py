# services.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import UsageEvent, Plan, Subscription


from datetime import datetime 
from sqlalchemy import func, select
from sqlalchemy.orm import Session



class MeterService:
    def __init__(self, db: Session):
        self.db = db

    def get_subscription(self, tenant_id: int):
          return self.db.scalar(
            select(Subscription).where(Subscription.tenant_id == tenant_id, Subscription.status == "active",)
            )

    def get_plan(self, subscription):
        return self.db.get(Plan, subscription.plan_id)

    
    def get_monthly_usage(self, tenant_id: int, usage_type: str):
        start_of_month = datetime.utcnow().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return self.db.scalar(
            select(func.coalesce(func.sum(UsageEvent.quantity), 0))
            .where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.usage_type == usage_type,
                UsageEvent.created_at >= start_of_month,
            )
        )

    # this complete the idempotency requirement
    def record(self, tenant_id: int, usage_type:str, quantity: int, idempotency_key: str):
        existing = self.db.scalar(
                select(UsageEvent).where(UsageEvent.tenant_id == tenant_id, UsageEvent.idempotency_key == idempotency_key))
        if existing:
            return existing

        subscription = self.get_subscription(tenant_id)

        if not subscription:
            raise ValueError("Tenant has no active subscription")

        current_usage = self.get_monthly_usage(tenant_id, usage_type) or 0

        plan = self.get_plan(subscription)

        if not plan:
            raise ValueError("Active subscription has no associated plan")

        if usage_type == "api_call":
            if current_usage + quantity > plan.api_call_quota:
                raise PermissionError(
                    f"API call quota exceeded. "
                    f"Limit: {plan.api_call_quota}, "
                    f"current usage: {current_usage}"
                )

        event = UsageEvent(
            tenant_id=tenant_id,usage_type=usage_type,quantity=quantity,idempotency_key=idempotency_key,)
        
        self.db.add(event)
        self.db.commit()
        return event



    