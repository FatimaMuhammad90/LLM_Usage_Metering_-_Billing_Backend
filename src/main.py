from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from .schemas import UsageRequest
from .services import MeterService
from .db import sessionLocal
from fastapi import Depends, FastAPI, HTTPException


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
