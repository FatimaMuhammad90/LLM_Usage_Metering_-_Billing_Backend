# BUILDLOG.md - Usage Metering & Billing Engine

## Architecture Overview

### System Architecture


---

## Key System Decisions

### 1. Database Choice: PostgreSQL with Docker
- **Decision:** PostgreSQL running in Docker container
- **Reason:** Production-ready, ACID compliant, easy to run locally
- **Alternative considered:** SQLite 

### 2. Idempotency Strategy
- **Decision:** Database unique constraint on `(tenant_id, idempotency_key)`
- **Implementation:** `UniqueConstraint` in `UsageEvent` model
- **Why this approach:** Database-level enforcement is atomic and reliable
- **Alternative considered:** Application-level cache (less reliable)

### 3. Quota Enforcement
- **Decision:** Check before recording, raise PermissionError
- **Implementation:** `MeterService.record()` validates before creating event
- **Status codes:** 429 Too Many Requests for quota exceeded
- **Why:** Honest API boundaries with clear error messages

### 4. Money Storage
- **Decision:** Store all monetary values as integers (cents)
- **Example:** $29.00 stored as 2900 cents
- **Why:** Avoid floating point precision errors
- **Standard:** Always convert to cents before storing

### 5. AI Token Pricing Model
- **Decision:** Per-token pricing with special rules:
  - Cached input tokens: 50 (cheaper than standard 100)
  - Standard input tokens: 100
  - Output tokens: 300
  - Reasoning tokens: count as output (300)
- **Why:** Real-world AI pricing is complex and must be correct

### 6. Stripe Integration
- **Decision:** Use Stripe Checkout + Webhooks
- **Approach:**
  1. Create checkout session with metadata
  2. Customer completes payment on Stripe
  3. Webhook updates local database
  4. Signature verification prevents forged events
  5. Deduplication prevents double processing
- **Why:** Standard pattern for SaaS billing

### 7. Testing Strategy
- **Decision:** SQLite in-memory for tests
- **Why:**
  - No Docker/PostgreSQL required
  - Fast execution
  - Isolated tests
  - Teacher can run immediately

### 8. Background Job
- **Decision:** Usage Alerts at 80% and 100% quota
- **Implementation:** `jobs/usage_alerts.py`
- **Automation:** GitHub Actions workflow scheduled daily (Tried but we require cloud hosting of the database, which was not yet implemented, so it is kept manual)
- **Why:** Proactive monitoring, easy to demo

---

## AI Usage Log

### What Was Built with AI Assistance

#### 1. Seed.py
- **What:** Database seeding script for Free and Pro plans
- **How AI helped:** Generated the initial script structure and plan data
- **My input:** Specified plan names, quotas, and pricing

#### 2. Pricing Module (`pricing.py`)
- **What:** AI token pricing calculation with cached/reasoning token rules
- **How AI helped:** Wrote the calculation logic with proper pricing rules
- **My input:** Specified the pricing constants and rules
- **Why AI:** Pricing rules are complex and easy to get wrong

#### 3. MeterService (`services.py`)
- **What:** Core usage metering and quota enforcement logic
- **How AI helped:** Generated the `get_monthly_usage` aggregation function
- **My input:** Defined the business requirements and logic flow
- **Note:** AI made the code more compact and efficient than my initial version

#### 4. Webhook Endpoint (`main.py` - `/webhooks/stripe`)
- **What:** Stripe webhook handler with signature verification and deduplication
- **How AI helped:** 
  - Explained Stripe webhook signature verification
  - Solved metadata alignment issues causing crashes
  - Wrote the `.to_dict()` conversion to handle StripeObject properly
  - Added error handling for test events without metadata
- **My input:** Understood the Stripe flow conceptually but needed help with implementation details
- **Why AI:** Stripe webhooks have tricky edge cases (signature verification, event deduplication, metadata access)

#### 5. Tests
- **What:** Test files for idempotency, quotas, pricing, and webhooks
- **How AI helped:** Generated test structure and edge cases
- **My input:** Defined what needed to be tested
- **Why AI:** Testing billing systems requires many edge cases I wouldn't have thought of

#### 6. Background Job (`jobs/usage_alerts.py`)
- **What:** Usage alert system for 80% and 100% thresholds
- **How AI helped:** Generated the alert logic and GitHub Actions workflow
- **My input:** Defined the threshold percentages and alert format

---

## Issues Encountered & Fixes

### Issue 1: Webhook KeyError on 'tenant_id'
- **Problem:** Stripe test events from `stripe trigger` had no metadata
- **Fix:** Added check for empty metadata before accessing
- **Lesson:** Always handle test/edge cases gracefully

### Issue 2: AttributeError 'get' on StripeObject
- **Problem:** StripeObject doesn't have `.get()` method
- **Fix:** Convert to dict with `.to_dict()` before accessing
- **Lesson:** Understand Stripe's API objects vs Python dicts

### Issue 3: Pricing Tests Failing
- **Problem:** Cost calculation mismatch (100 vs 100000)
- **Fix:** Removed division by 1000 - pricing constants are per-token
- **Lesson:** Understand the unit of pricing constants

### Issue 4: Duplicate Checkout Endpoint
- **Problem:** Two identical `/billing/checkout` endpoints
- **Fix:** Removed duplicate, kept the one with proper error handling
- **Lesson:** Review code for duplicates before committing

### Issue 5: Missing Idempotency Key in Tests
- **Problem:** Tests failing because `idempotency_key` was required
- **Fix:** Added `idempotency_key` to all test `record()` calls
- **Lesson:** Tests must match actual API contracts

### Issue 6: Database Connection Refused
- **Problem:** Docker not running when trying to use app
- **Fix:** Tests use SQLite in-memory, no Docker needed
- **Lesson:** Separate test environment from development

---

## What Worked Well

1. **Idempotency Design:** Database-level unique constraint
2. **SQLite for Tests:** Tests run fast without Docker
3. **Stripe Webhook Deduplication:** Prevents double-processing
4. **AI Token Pricing:** Pricing rules correctly implemented and tested
5. **Background Job:** Usage alerts work and are easy to demonstrate

---

## What I'd Do Differently

1. **Cloud Database:** Would use Supabase/Railway for GitHub Actions integration
2. **More Tests:** Add integration tests with actual Stripe API calls
3. **Better Logging:** Add structured logging for production debugging
4. **Monitoring:** Add metrics for usage and billing events



**AI assistance:** Heavy on Stripe/webhook implementation, testing, and documentation. Light on overall architecture and database design and pricing logic (my expertise).

