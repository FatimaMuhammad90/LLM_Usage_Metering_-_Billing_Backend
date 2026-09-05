from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from .schemas import UsageRequest
from .services import MeterService
from .db import sessionLocal

app = FastAPI()


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

    event = meter.record(tenant_id=tenant_id, usage_type=request.usage_type, quantity=request.quantity, idempotency_key=request.idempotency_key)

    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "usage_type": event.usage_type,
        "quantity": event.quantity,
        "idempotency_key": event.idempotency_key,
    }
