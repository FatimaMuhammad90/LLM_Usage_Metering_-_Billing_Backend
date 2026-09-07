# Usage Metering & Billing Engine

A backend service for tracking tenant API usage, enforcing subscription quotas, calculating usage costs, and integrating Stripe test-mode billing.

The system is designed around reliable usage metering with tenant isolation and exactly-once processing for usage events. It supports Free and Pro subscription plans, monthly usage aggregation, quota enforcement, AI token pricing, cached input token pricing, reasoning token handling, Stripe Checkout, signed webhook processing, idempotent webhook handling, and usage alerts.

## Features

* Multi-tenant usage tracking
* Exactly-once usage recording using tenant-scoped idempotency keys
* Monthly usage aggregation
* Subscription and plan management
* API-call quota enforcement
* Exact quota-boundary handling
* HTTP `429 Too Many Requests` responses when quotas are exceeded
* API usage cost calculation
* AI token pricing
* Cached input token pricing
* Reasoning token handling
* Dummy AI generation endpoint
* Stripe Checkout integration in test mode
* Signed Stripe webhook verification
* Idempotent Stripe webhook processing
* Automatic tenant plan updates after successful Stripe events
* Usage threshold alerts
* Automated usage-alert job
* PostgreSQL database
* SQLite in-memory testing database
* Automated test suite
* Docker support
* FastAPI interactive API documentation

## Architecture

The application follows a simple service-oriented backend structure:

```text
Client
  |
  v
FastAPI API
  |
  +-------------------+
  |                   |
  v                   v
MeterService       Stripe Service
  |                   |
  v                   v
PostgreSQL          Stripe API
  |
  +----------------------+
  |          |           |
  v          v           v
Tenants    Plans    Usage Events
             |
             v
        Subscriptions
```

### Main Components

* **FastAPI** handles HTTP requests and API endpoints.
* **SQLAlchemy** provides database access and ORM models.
* **PostgreSQL** is used as the production-style database.
* **MeterService (in services.py)** contains usage metering and quota logic.
* **Stripe** handles test-mode Checkout and subscription events.
* **Stripe webhooks** synchronize billing state with the local database.
* **Usage alerts job** detects tenants approaching or exceeding their quotas.
* **Pytest** provides automated testing.
* **Docker** provides reproducible database/application environments.

## Tech Stack

| Technology    | Purpose                   |
| ------------- | ------------------------- |
| Python 3.11   | Backend language          |
| FastAPI       | REST API framework        |
| SQLAlchemy    | ORM/database access       |
| PostgreSQL    | Main database             |
| SQLite        | Testing database          |
| Stripe        | Test-mode billing         |
| Pydantic      | Request validation        |
| Pytest        | Automated testing         |
| Docker        | Containerization          |
| Uvicorn       | ASGI server               |
| python-dotenv | Environment configuration |

## Project Structure (Local structure)

```text
capstone/
│
├── jobs/
│   └── usage_alerts.py
│
├── src/
│   ├── __init__.py
│   ├── create_stripe_script.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   ├── pricing.py
│   ├── schemas.py
│   ├── seed.py
│   ├── services.py
│   └── stripe_service.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_idempotency.py
│   ├── test_pricing.py
│   ├── test_quotas.py
│   └── test_webhooks.py
│
├── .env
├── .env.example
├── .gitignore
├── BUILDLOG.MD
├── capstone.yaml
├── docker-compose.yaml
├── Dockerfile
├── EVIDENCE.md
└── README.md
```

# Database Design

The system uses four core business tables plus a Stripe webhook event table.

## Tenants

Stores customers using the metering system.

```text
id
name
created_at
```

Each tenant has its own subscription and usage records.

## Plans

Stores available subscription plans and their quotas.

```text
id
name
api_call_quota
monthly_price_cents
created_at
```

The project contains Free and Pro plans.

## Subscriptions

Connects a tenant to its current plan.

```text
id
tenant_id
plan_id
status
stripe_customer_id
stripe_subscription_id
created_at
```

Stripe identifiers are stored when billing events provide them.

## Usage Events

Stores individual usage events.

```text
id
tenant_id
usage_type
quantity
idempotency_key
created_at
```

A composite unique constraint is applied to:

```text
tenant_id + idempotency_key
```

This means the same idempotency key cannot create two usage events for the same tenant.

Different tenants can independently use the same key.

## Stripe Events

Stores processed Stripe event IDs.

```text
id
stripe_event_id
created_at
```

The Stripe event ID is unique, allowing webhook replay protection.

# API Endpoints

## 1. Health Check

### `GET /`

Returns a basic response confirming that the API is running.

Example:

```http
GET /
```

# Tenant Management

## 2. Create Tenant

### `POST /tenants`

Creates a new tenant and automatically assigns the Free plan.

### Request

```json
{
  "name": "Example Tenant"
}
```

### Response

```json
{
  "tenant_id": 1,
  "name": "Example Tenant",
  "plan": "Free",
  "subscription_status": "active"
}
```

The tenant receives an active subscription associated with the Free plan.

# Usage Metering

## 3. Record Usage

### `POST /tenants/{tenant_id}/usage`

Records usage for a tenant.

### Request

```json
{
  "usage_type": "api_call",
  "quantity": 1,
  "idempotency_key": "request-123"
}
```

### Example

```http
POST /tenants/1/usage
```

```json
{
  "usage_type": "api_call",
  "quantity": 1,
  "idempotency_key": "request-123"
}
```

### Successful Response

The usage event is stored and assigned an ID.

### Idempotency

If the same tenant sends the same `idempotency_key` again, the existing usage event is returned instead of creating another event.

For example:

```text
Request 1:
idempotency_key = request-123
quantity = 1

Request 2:
idempotency_key = request-123
quantity = 1
```

Only one usage event is recorded.

This prevents duplicate billing or usage caused by retries.

# Quota Enforcement

API usage is checked against the tenant's current subscription quota.

Before creating a new usage event, the service calculates:

```text
current monthly usage + requested quantity
```

If the result exceeds the plan quota, the request is rejected.

Example:

```text
Quota: 100 API calls
Current usage: 99
Requested: 1
Result: allowed

Current usage: 100
Requested: 1
Result: rejected
```

The API returns:

```http
429 Too Many Requests
```

when the quota would be exceeded.

The quota boundary is therefore enforced exactly.

Importantly, an existing idempotent request is resolved before quota rejection. Retrying an already-recorded request does not create another event or incorrectly fail because the tenant has since reached its quota.

# Monthly Usage

## 4. Get Tenant Usage

### `GET /tenants/{tenant_id}/usage`

Returns the tenant's current monthly usage and calculated cost.

Example:

```http
GET /tenants/1/usage
```

The endpoint reports usage categories such as:

```text
API calls
AI tokens
API cost
AI cost
Total cost
```

Usage is calculated from events belonging to the current calendar month.

# AI Generation

## 5. Dummy AI Generation

### `POST /tenants/{tenant_id}/generate`

Simulates an AI generation request.

The endpoint does not call a real AI model.

Instead, it generates a simulated token usage amount and records it as AI token usage.

Example:

```http
POST /tenants/1/generate
```

This allows the metering and pricing system to be demonstrated without requiring an external AI provider or API key.

# AI Token Pricing

AI usage supports different token categories.

The pricing model distinguishes between:

* Standard input tokens
* Cached input tokens
* Output tokens
* Reasoning tokens

Cached input tokens use a lower price than standard input tokens.

Reasoning tokens are treated as output tokens for billing purposes.

The pricing implementation is centralized in:

```text
src/pricing.py
```

This prevents pricing logic from being duplicated throughout the application.

All monetary calculations use integer-based pricing constants to avoid floating-point billing errors.

# Stripe Billing

Stripe integration is implemented using Stripe test mode.

The application does not process real payments.

## 6. Create Stripe Checkout Session

### `POST /tenants/{tenant_id}/billing/checkout`

Creates a Stripe Checkout session for upgrading a tenant.

The Checkout session is created in subscription mode.

Example:

```http
POST /tenants/1/billing/checkout
```

The endpoint returns the Checkout session information, including the Stripe Checkout URL.

The customer can use Stripe's test environment to complete the simulated subscription purchase.

# Stripe Webhooks

## 7. Stripe Webhook

### `POST /webhooks/stripe`

Receives Stripe webhook events.

The endpoint:

1. Reads the raw webhook body.
2. Reads the Stripe signature.
3. Verifies the signature using the configured webhook secret.
4. Extracts the Stripe event ID.
5. Checks whether the event has already been processed.
6. Ignores duplicate events.
7. Updates the tenant subscription when appropriate.
8. Stores the processed event ID.

## Supported Stripe Events

The application handles events including:

```text
checkout.session.completed
customer.subscription.updated
customer.subscription.deleted
```

### Checkout Completion

When Checkout is successfully completed, the tenant's subscription information is updated.

### Subscription Update

When Stripe reports a subscription change, the corresponding local subscription is updated.

### Subscription Deletion

When a subscription is deleted, the local subscription status is updated accordingly.

# Webhook Security

Stripe webhook signatures are verified before any event is processed.

Invalid signatures result in:

```http
400 Bad Request
```

The application does not trust the contents of an unsigned or incorrectly signed webhook.

This protects the billing endpoint from forged requests.

# Webhook Idempotency

Stripe may deliver the same webhook event more than once.

To prevent duplicate processing, each Stripe event ID is stored in the `stripe_events` table.

For example:

```text
Event ID: evt_123

First delivery:
Processed -> stored

Second delivery:
Already exists -> ignored
```

This makes webhook handling idempotent.

# Usage Alerts

Usage alerts are implemented in:

```text
jobs/usage_alerts.py
```

The job checks active subscriptions and compares monthly API usage against the plan quota.

Two alert levels are supported.

### Warning

Triggered when usage reaches:

```text
80% of quota
```

### Critical

Triggered when usage reaches:

```text
100% or more of quota
```

Example:

```text
API quota: 100

Usage: 80
Alert: WARNING

Usage: 100
Alert: CRITICAL
```

The alert job does not create additional usage events. It only monitors existing usage and reports tenants that have reached the configured thresholds.

# Admin Alert Endpoint

## 8. Run Usage Alerts

### `POST /admin/alerts`

Runs the usage alert check.

Example:

```http
POST /admin/alerts
```

The endpoint executes the alert job and returns the generated alerts.

This provides a simple way to demonstrate the monitoring functionality during evaluation.

# Request Validation

Pydantic schemas validate incoming API requests.

For example, usage requests require:

```text
usage_type
quantity
idempotency_key
```

The quantity must be greater than zero.

The idempotency key must not be empty.

Invalid requests are rejected before business logic is executed.

# Tenant Isolation

All usage events are associated with a `tenant_id`.

Usage calculations always filter by the requested tenant.

This ensures that one tenant's usage is not included in another tenant's totals.

The idempotency constraint is also tenant-scoped:

```text
(tenant_id, idempotency_key)
```

rather than globally scoped.

# Environment Variables

Create a `.env` file using `.env.example` as a template.

Example:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/metering

STRIPE_SECRET_KEY=your_stripe_test_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

Never commit real Stripe credentials or other secrets.

# Running the Project Locally

## 1. Clone the Repository

```bash
git clone <repository-url>
cd capstone
```

## 2. Create a Virtual Environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Start PostgreSQL

The project provides a Docker Compose configuration.

```bash
docker compose up -d
```

Check the database container:

```bash
docker compose ps
```

PostgreSQL is exposed on:

```text
localhost:5432
```

## 5. Configure Environment Variables

Create:

```text
.env
```

and configure the database and Stripe test credentials.

## 6. Seed the Database

Run the project's seed script:

```bash
python -m src.seed
```

This creates the initial Free and Pro plans.

## 7. Start the API

If using the virtual environment directly on Windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

# API Documentation

FastAPI automatically provides interactive documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

Swagger UI can be used to create tenants, record usage, check quotas, create Checkout sessions, and test the other endpoints.

# Stripe Test Mode

The Stripe CLI can be used to forward webhook events to the local API.

Start the webhook listener:

```bash
stripe listen --forward-to http://127.0.0.1:8000/webhooks/stripe
```

Stripe CLI will provide a webhook signing secret.

Set that secret in `.env`:

```env
STRIPE_WEBHOOK_SECRET=your_webhook_secret
```

Restart the API after changing environment variables.

## Triggering Stripe Test Events

Stripe CLI can be used to generate test webhook events.

Example:

```bash
stripe trigger checkout.session.completed
```

Other Stripe test events can also be generated through the CLI.

The webhook endpoint verifies the Stripe signature before processing the event.

# Testing

The project uses Pytest.

Run the complete test suite with:

```bash
pytest tests/ -v
```

The tests cover the major requirements of the billing and metering engine.

## Idempotency Tests

`tests/test_idempotency.py`

Tests include:

* Duplicate usage does not create duplicate events.
* Different idempotency keys create separate events.
* Multiple retries remain idempotent.

Example scenario:

```text
POST usage
    |
    v
event created
    |
    v
retry same request
    |
    v
existing event returned

database:
1 usage event
```

## Quota Tests

`tests/test_quotas.py`

Tests include:

* Usage below the quota is accepted.
* Usage exactly at the quota is accepted.
* Usage exceeding the quota is rejected.
* Pro users receive the higher quota.

The tests specifically verify the quota boundary rather than only testing an obviously over-limit request.

## Pricing Tests

`tests/test_pricing.py`

Tests include:

* Cached tokens are cheaper than standard input tokens.
* Reasoning tokens count as output tokens.
* Mixed token categories are calculated correctly.
* Pricing constants remain pinned.
* Negative costs are prevented.

## Webhook Tests

`tests/test_webhooks.py`

Tests include:

* Duplicate Stripe events are ignored.
* Subscription upgrades update the tenant plan.
* Invalid webhook signatures are rejected.

# Testing Database

The automated tests use an isolated SQLite in-memory database.

This provides:

* Fast tests
* No dependency on the local PostgreSQL server
* Test isolation
* No modification of development data

PostgreSQL remains the main database used by the application during normal operation.

# Docker

The project includes Docker support.

## Dockerfile

The application Dockerfile uses Python 3.11 and starts the FastAPI server with Uvicorn.

Example:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose

Docker Compose is used to run PostgreSQL.

```bash
docker compose up -d
```

Stop the containers with:

```bash
docker compose down
```

# Example Usage Flow

A typical application flow is:

```text
1. Create tenant
        |
        v
2. Tenant receives Free subscription
        |
        v
3. Record API usage
        |
        v
4. Usage event stored
        |
        v
5. Monthly usage calculated
        |
        v
6. Quota checked
        |
        +---- Under quota ----> Request accepted
        |
        +---- Over quota -----> HTTP 429
        |
        v
7. Tenant approaches quota
        |
        v
8. Usage alert generated
        |
        v
9. Tenant upgrades through Stripe
        |
        v
10. Stripe webhook received
        |
        v
11. Webhook signature verified
        |
        v
12. Tenant subscription updated
        |
        v
13. Higher quota becomes available
```

# Example Idempotency Flow

```text
Client
  |
  | POST /usage
  | key = abc123
  v
API
  |
  | Check tenant + key
  v
No existing event
  |
  | Create event
  v
Database
```

If the client retries:

```text
Client
  |
  | POST /usage
  | key = abc123
  v
API
  |
  | Check tenant + key
  v
Existing event found
  |
  v
Return existing result
```

No second usage event is created.

# Example Quota Flow

For a Free plan with a quota of 100 API calls:

```text
Current usage = 99
Requested     = 1

99 + 1 = 100

Result: ACCEPTED
```

If the tenant is already at 100:

```text
Current usage = 100
Requested     = 1

100 + 1 = 101

Result: HTTP 429
```

This ensures that usage cannot exceed the configured subscription quota.

# Security Considerations

The project includes several protections relevant to a billing and metering system:

* Stripe webhook signature verification
* Stripe event deduplication
* Tenant-scoped idempotency
* Database uniqueness constraints
* Request validation using Pydantic
* No secrets stored in source code
* Environment-based configuration
* Tenant-specific usage queries
* Test-mode Stripe integration

# Design Decisions

## Why Use Idempotency Keys?

Network requests can be retried.

Without idempotency, a request could be processed twice:

```text
Client sends usage
       |
       v
Server records usage
       |
       X
Response lost
       |
       v
Client retries
       |
       v
Usage recorded again
```

The idempotency key allows the server to recognize that the retry represents the same logical request.

## Why Use a Database Uniqueness Constraint?

Application-level checks alone are not sufficient to guarantee uniqueness under concurrent requests.

The database constraint:

```text
UNIQUE(tenant_id, idempotency_key)
```

provides an additional integrity guarantee.

## Why Store Stripe Event IDs?

Stripe webhooks can be delivered more than once.

Persisting the event ID makes webhook processing idempotent and prevents the same event from changing billing state multiple times.

# Scope and Limitations

This project intentionally focuses on the core usage metering and subscription billing requirements.

It does not implement:

* Real AI model inference
* Production payment processing
* Invoice generation
* Proration
* Complex overage billing
* Tax calculation
* Refund management
* Full production authentication/authorization
* Real-time distributed metering infrastructure

The AI generation endpoint is intentionally simulated so that token metering and pricing can be demonstrated without making external AI API calls.

Stripe is used in test mode.

# Evidence

Implementation and demonstration evidence is documented separately in:

```text
EVIDENCE.md
```

The evidence includes demonstrations of:

* Tenant creation
* Subscription status
* Stripe Checkout
* Free-to-Pro upgrade
* Usage idempotency
* Quota enforcement
* Usage alerts
* 80% usage warning
* 100% usage critical alert

# Build Log

Development decisions and implementation progress are documented in:

```text
BUILDLOG.MD
```

# Configuration Files

The project includes:

```text
.env.example
capstone.yaml
docker-compose.yaml
Dockerfile
```

These provide the configuration required to reproduce the development environment.

Real secrets must remain in `.env` and must not be committed to version control.

# Running the Complete System

A typical local development setup is:

### Terminal 1 — PostgreSQL

```bash
docker compose up -d
```

### Terminal 2 — FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload
```

### Terminal 3 — Stripe CLI

```bash
stripe listen --forward-to http://127.0.0.1:8000/webhooks/stripe
```

Then open:

```text
http://127.0.0.1:8000/docs
```

# Evaluation Demonstration

The main functionality can be demonstrated through the following sequence:

### 1. Create a Tenant

```http
POST /tenants
```

### 2. Check the Tenant's Plan

```http
GET /tenants/{tenant_id}/usage
```

### 3. Record Usage

```http
POST /tenants/{tenant_id}/usage
```

### 4. Repeat the Same Request

Use the same:

```text
idempotency_key
```

and verify that usage is not double-counted.

### 5. Reach the Quota

Continue sending usage until the quota boundary is reached.

### 6. Exceed the Quota

Send one additional usage request and verify:

```http
429 Too Many Requests
```

### 7. Create a Stripe Checkout Session

```http
POST /tenants/{tenant_id}/billing/checkout
```

### 8. Complete the Stripe Test Checkout

Use Stripe test mode.

### 9. Receive the Webhook

Stripe CLI forwards the webhook to:

```text
POST /webhooks/stripe
```

### 10. Verify the Plan Update

Check the tenant's subscription and usage information.

### 11. Test a Forged Webhook

Send an invalid signature and verify:

```http
400 Bad Request
```

### 12. Replay a Valid Event

Send the same Stripe event again and verify that it is ignored.

### 13. Run Usage Alerts

```http
POST /admin/alerts
```

Verify warning and critical alerts at the configured thresholds.

# Project Status

The project implements the core requirements of a usage metering and billing backend, including:

* Tenant management
* Subscription plans
* Usage tracking
* Idempotent metering
* Monthly aggregation
* Quota enforcement
* AI token pricing
* Stripe Checkout
* Signed Stripe webhooks
* Webhook deduplication
* Usage monitoring
* Automated tests
* PostgreSQL
* Docker support

The remaining project work primarily consists of documentation and evidence formatting rather than core backend functionality.

## License

This project was developed as part of an internship/capstone project and is intended for educational and evaluation purposes.
