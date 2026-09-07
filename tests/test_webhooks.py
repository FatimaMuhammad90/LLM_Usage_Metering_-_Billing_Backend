import pytest
from src.models import StripeEvent, Subscription, Plan

def test_webhook_deduplication(db_session):

    event_id = "evt_test_123"
    
    stripe_event1 = StripeEvent(stripe_event_id=event_id)
    db_session.add(stripe_event1)
    db_session.commit()
    
    existing = db_session.query(StripeEvent).filter(
        StripeEvent.stripe_event_id == event_id
    ).first()
    
    assert existing is not None, "First event not stored!"
    assert existing.stripe_event_id == event_id, "Wrong event ID!"
    
    count = db_session.query(StripeEvent).count()
    assert count == 1, f"Expected 1 event, got {count}"
    
    print(f"Webhook deduplication test PASSED! Duplicate ignored.")


def test_subscription_upgrade(db_session, test_tenant, test_subscription):

    # Before: Free plan
    assert test_subscription.plan_id == 1, "Not on Free plan!"
    assert test_subscription.status == "active", "Not active!"
    
    # Upgrade to Pro (plan_id=2)
    pro_plan = db_session.query(Plan).filter(Plan.name == "Pro").first()
    test_subscription.plan_id = pro_plan.id
    db_session.commit()
    
    # After: Pro plan
    updated = db_session.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    
    assert updated.plan_id == 2, "Not on Pro plan!"
    
    print(f"Subscription upgrade test PASSED! Upgraded to Pro.")