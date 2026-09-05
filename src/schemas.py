from pydantic import BaseModel, Field

class UsageRequest(BaseModel):
    usage_type: str
    quantity: int = Field(gt=0)
    idempotency_key: str = Field( min_length=1)