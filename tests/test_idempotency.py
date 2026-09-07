import pytest
from src.models import UsageEvent


def test_idempotency_prevents_double_counting(db_session, meter_service, test_tenant):

    event1 = meter_service.record( tenant_id=test_tenant.id, usage_type="api_call", quantity=10,idempotency_key="test-key-123")

    print(f" First request: event_id={event1.id}, quantity={event1.quantity}")

    event2 = meter_service.record(tenant_id=test_tenant.id, usage_type="api_call", quantity=999,  idempotency_key="test-key-123")

    print(f"Second request: event_id={event2.id}, quantity={event2.quantity}")

    assert event1.id == event2.id, "Different events returned"
    assert event1.quantity == 10, "Quantity changed"
    assert event2.quantity == 10, " Second request didn't return original quantity"

    count = db_session.query(UsageEvent).count()
    assert count == 1, f"Expected 1 event, got {count}"
    
    print(f"Idempotency test PASSED! One event created, duplicate ignored.")


def test_different_keys_create_different_events(db_session, meter_service, test_tenant):

    event1 = meter_service.record( tenant_id=test_tenant.id, usage_type="api_call", quantity=10, idempotency_key="key-1")
    
    event2 = meter_service.record( tenant_id=test_tenant.id, usage_type="api_call",quantity=20, idempotency_key="key-2")   


    assert event1.id != event2.id, "Different keys created same event"
    assert event1.quantity == 10, "Event1 quantity wrong"
    assert event2.quantity == 20, "Event2 quantity wrong"
    
    count = db_session.query(UsageEvent).count()
    assert count == 2, f"Expected 2 events, got {count}"
    
    print(f"Different keys test PASSED! Two events created.")



def test_idempotency_with_multiple_retries(db_session, meter_service, test_tenant):

    events = []
    for i in range(5):
        event = meter_service.record(
            tenant_id=test_tenant.id,
            usage_type="api_call",
            quantity=10,
            idempotency_key="retry-key"
        )
        events.append(event.id)

    assert all(id == events[0] for id in events), "Different IDs on retry!"

    count = db_session.query(UsageEvent).count()

    assert count == 1, f"Expected 1 event, got {count} after 5 retries!"
    
    print(f"5 retries test PASSED! Only one event created.")

