from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import UsageEvent

class MeterService:
    def __init__(self, db: Session):
        self.db = db

    # this complete the idempotency requirement
    def record(self, tenant_id: int, usage_type:str, quantity: int, idempotency_key: str):
        existing = self.db.scalar(
                select(UsageEvent).where(UsageEvent.tenant_id == tenant_id, UsageEvent.idempotency_key == idempotency_key),
            )
        if existing:
            return existing

        event = UsageEvent(
            tenant_id=tenant_id,usage_type=usage_type,quantity=quantity,idempotency_key=idempotency_key,)
        
        self.db.add(event)
        self.db.commit()
        return event