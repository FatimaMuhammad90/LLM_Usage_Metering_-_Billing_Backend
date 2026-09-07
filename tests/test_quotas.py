
import pytest
from src.services import MeterService

def test_quota_allows_usage_under_limit(db_session, meter_service, test_tenant):

    event = meter_service.record(
        tenant_id=test_tenant.id,
        usage_type="api_call",
        quantity=50, 
        idempotency_key="under-limit"  #idempotency_key
    )
    
    assert event is not None, "Event not created!"
    assert event.quantity == 50, "Wrong quantity!"
    
    usage = meter_service.get_monthly_usage(test_tenant.id, "api_call")
    assert usage == 50, f"Expected 50, got {usage}"
    
    print(f"Under quota test PASSED! Usage: {usage}/100")


def test_quota_at_exact_limit(db_session, meter_service, test_tenant):

    event = meter_service.record(
        tenant_id=test_tenant.id,
        usage_type="api_call",
        quantity=100,  # Exactly at limit
        idempotency_key="at-limit"  # Added idempotency_key
    )
    
    assert event is not None, "Event not created!"
    
    usage = meter_service.get_monthly_usage(test_tenant.id, "api_call")
    assert usage == 100, f"Expected 100, got {usage}"
    
    print(f"At limit test PASSED! Usage: {usage}/100")


def test_quota_exceeds_limit(db_session, meter_service, test_tenant):

    meter_service.record(
        tenant_id=test_tenant.id,
        usage_type="api_call",
        quantity=90,
        idempotency_key="near-limit"
    )

    with pytest.raises(PermissionError) as exc_info:
        meter_service.record(
            tenant_id=test_tenant.id,
            usage_type="api_call",
            quantity=20,
            idempotency_key="exceed-limit"
        )
    
    error_msg = str(exc_info.value).lower()
    assert "quota exceeded" in error_msg, "Wrong error message!"
    
    usage = meter_service.get_monthly_usage(test_tenant.id, "api_call")
    assert usage == 90, f"Usage should still be 90, got {usage}"
    
    print(f"Quota exceeded test PASSED! Blocked request, usage: {usage}/100")


def test_pro_plan_higher_limit(db_session, meter_service, pro_tenant):
    """
    Test: Pro plan should have higher limit (1000)
    """
    print("\nTesting Pro plan limit...")
    
    # Record 500 API calls (allowed on Pro)
    event = meter_service.record(
        tenant_id=pro_tenant.id,
        usage_type="api_call",
        quantity=500,
        idempotency_key="pro-usage"  # Added idempotency_key
    )
    
    assert event is not None, "Pro plan event not created!"
    
    usage = meter_service.get_monthly_usage(pro_tenant.id, "api_call")
    assert usage == 500, f"Expected 500, got {usage}"
 
    subscription = meter_service.get_subscription(pro_tenant.id)
    plan = meter_service.get_plan(subscription)
    assert plan.name == "Pro", "Not on Pro plan!"
    assert plan.api_call_quota == 1000, "Wrong quota for Pro!"
    
    print(f"Pro plan test PASSED! Usage: {usage}/1000")