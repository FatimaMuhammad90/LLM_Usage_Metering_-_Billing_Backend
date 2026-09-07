import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.db import Base
from src.models import Tenant, Plan, Subscription, UsageEvent
from src.services import MeterService



@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:",connect_args={"check_same_thread": False})

    Base.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()


    free_plan = Plan(name="Free",api_call_quota=100, monthly_price_cents=0)

    pro_plan = Plan( name="Pro", api_call_quota=1000, monthly_price_cents=2900)


    session.add_all([free_plan, pro_plan])
    session.commit()

    tenant = Tenant(name="Test Tenant")
    session.add(tenant)
    session.flush()
    
    subscription = Subscription(
        tenant_id=tenant.id,
        plan_id=free_plan.id,
        status="active"
    )
    session.add(subscription)
    session.commit()

    yield session
    
    session.close()


@pytest.fixture
def meter_service(db_session):
    return MeterService(db_session)


@pytest.fixture
def test_tenant(db_session):
    return db_session.query(Tenant).first()


@pytest.fixture
def test_subscription(db_session, test_tenant):
    return db_session.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()


@pytest.fixture
def pro_tenant(db_session):

    pro_plan = db_session.query(Plan).filter(Plan.name == "Pro").first()
    
    tenant = Tenant(name="Pro Tenant")
    db_session.add(tenant)
    db_session.flush()

      
    # Create subscription with Pro plan
    subscription = Subscription(
        tenant_id=tenant.id,
        plan_id=pro_plan.id,
        status="active"
    )
    db_session.add(subscription)
    db_session.commit()
    
    return tenant
    