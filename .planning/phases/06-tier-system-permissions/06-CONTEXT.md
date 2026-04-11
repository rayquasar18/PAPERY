# Phase 6: Tier System & Permissions - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the SaaS tier/subscription system: Tier data model with configurable feature limits, centralized feature flag checking, usage tracking with monthly reset, and Stripe billing integration (Checkout Session + Customer Portal + webhooks). Rate limiting (anti-abuse) remains unchanged — this phase handles usage limits (tier-aware quotas).

</domain>

<decisions>
## Implementation Decisions

### Tier Data Model
- **D-01:** Hybrid storage approach — dedicated columns for core numeric limits (max_projects, max_docs_per_project, max_fixes_monthly, max_file_size_mb) + JSONB for dynamic data (allowed_models array, feature_flags object). Balances type safety with flexibility.
- **D-02:** Tier names updated from REQUIREMENTS.md — three default tiers: **free, pro, ultra** (not "enterprise"). User specified "ultra" during discussion.
- **D-03:** Dynamic tiers — admin can CRUD additional tiers beyond the 3 defaults. Supports custom plans, partnerships, promotional tiers.
- **D-04:** Auto-assign free tier — every new user automatically gets the "free" tier on registration. No null case. Replaces hardcoded `tier_name: str = "free"` in UserProfileRead (Phase 5 D-12).
- **D-05:** User → Tier FK — add `tier_id` foreign key to User model pointing to Tier table. Each user belongs to exactly one tier.

### Usage Limits (5 types)
- **D-06:** max_projects — total projects per account (dedicated column on Tier).
- **D-07:** max_docs_per_project — documents per project, NOT per account (dedicated column on Tier).
- **D-08:** max_fixes_monthly — monthly fix/edit operations quota, resets monthly (dedicated column on Tier).
- **D-09:** allowed_models — JSONB array of model slugs allowed per tier. E.g., free = ["gpt-4o-mini"], pro = ["gpt-4o", "claude-sonnet"], ultra = all models.
- **D-10:** max_file_size_mb — maximum upload file size per tier (dedicated column on Tier).

### Feature Flag System
- **D-11:** Dependency injection pattern — `Depends(require_feature('can_export_pdf'))` on routes. Consistent with existing `get_current_user` dependency pattern.
- **D-12:** Redis cache + TTL for tier data — cache tier/feature data in Redis (DB 0, cache namespace) with 5-minute TTL. Invalidate cache immediately when tier changes. Reduces DB queries by ~95%.
- **D-13:** Immediate permission update — when user upgrades/downgrades, permissions and usage limits take effect on the next request. No waiting for billing cycle end. Redis cache invalidation ensures this.

### Rate Limiting vs Usage Limits (IMPORTANT DISTINCTION)
- **D-14:** Rate limiting (anti-abuse) is UNCHANGED — existing `rate_limit.py` (Redis INCR+EXPIRE) stays as-is. Hardcoded limits, same for all users. NOT tier-aware. Prevents spam/DDoS.
- **D-15:** Usage limits are the tier-aware system — max projects, max docs, max fixes/month, model access, file size. These are business logic limits, not request rate limits.
- **D-16:** TIER-03 requirement reinterpretation — "Rate limiting is tier-aware" maps to usage limits, not traditional rate limiting. Usage limit enforcement uses dependency injection (same pattern as feature flags).

### Usage Tracking
- **D-17:** DB tracking table — `usage_tracking` table (user_id, metric, count, period_start, period_end). Monthly reset for time-based limits (fixes). Queryable for analytics.
- **D-18:** Usage check via dependency — `Depends(check_usage('documents'))` before creating a document. Checks current usage against tier limit. Returns 403 with limit details if exceeded.

### Stripe Billing Integration
- **D-19:** Stripe Checkout Session — redirect user to Stripe-hosted payment page for subscription. Simplest, most secure, PCI-compliant out of the box.
- **D-20:** Stripe Customer Portal — user self-manages subscription (upgrade, downgrade, cancel, update payment method) via Stripe-hosted portal. No custom billing UI needed.
- **D-21:** Full webhook event coverage — handle all relevant events:
  - `checkout.session.completed` — new subscription created
  - `customer.subscription.updated` — plan change (upgrade/downgrade)
  - `customer.subscription.deleted` — cancellation
  - `invoice.payment_failed` — payment failure
  - `invoice.paid` — successful payment
  - `customer.updated` — customer info change
  - `payment_method.attached` — new payment method
- **D-22:** Stripe test mode for development — use Stripe test API keys in development/staging. No real charges. Switch to live keys in production via environment variables.
- **D-23:** Webhook security — verify Stripe webhook signatures using endpoint secret. Reject unsigned/invalid payloads.

### Claude's Discretion
- Exact TTL duration for Redis tier cache (suggested 5 minutes, can adjust)
- Stripe webhook endpoint path and retry handling
- Usage tracking table schema details (indexes, constraints)
- Migration strategy for adding tier_id FK to existing User records

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/codebase/ARCHITECTURE.md` — Overall system architecture and layered pattern
- `.planning/codebase/CONVENTIONS.md` — Code conventions and patterns
- `.planning/codebase/STACK.md` — Technology stack details

### Prior Phase Context (Tier-Related)
- `.planning/phases/03-authentication-core-flows/03-CONTEXT.md` — D-11: unverified users allowed to login, feature restrictions by tier system
- `.planning/phases/05-user-profile-account-management/05-CONTEXT.md` — D-12: `tier_name: str = "free"` placeholder in UserProfileRead

### Existing Code
- `backend/app/utils/rate_limit.py` — Current rate limiting implementation (Redis INCR+EXPIRE) — remains unchanged
- `backend/app/models/user.py` — User model, needs tier_id FK addition
- `backend/app/schemas/user.py` — UserProfileRead with hardcoded tier_name placeholder
- `backend/app/models/base.py` — Base model with UUIDMixin, TimestampMixin, SoftDeleteMixin patterns
- `backend/app/infra/redis/client.py` — Redis client with 3 DB namespaces (cache, queue, rate_limit)
- `backend/app/services/auth_service.py` — AuthService pattern to follow for TierService
- `backend/app/services/user_service.py` — UserService pattern to follow

### Requirements
- `.planning/REQUIREMENTS.md` — TIER-01 through TIER-06 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseRepository[ModelType]` — generic async CRUD, extend for TierRepository and UsageTrackingRepository
- `rate_limit.py` — Redis INCR+EXPIRE pattern, can reference for usage tracking counters
- `AuthService` / `UserService` — service layer pattern with constructor DI, follow for TierService and StripeService
- `PaperyHTTPException` + subclasses (401, 403, 404, 409, 429) — reuse for tier/usage limit errors
- `get_current_user` dependency — pattern to follow for `require_feature()` and `check_usage()`
- Redis cache client (DB 0) — already available for tier data caching

### Established Patterns
- **Layered architecture:** Router → Dependencies → Service → Repository → Model
- **Schema separation:** Read, ReadInternal, Create, CreateInternal, Update variants
- **Dual ID:** int id (internal) + UUID (public API) — apply to Tier and UsageTracking models
- **Soft delete:** SoftDeleteMixin on all core entities — apply to Tier model
- **Config pattern:** Modular Pydantic Settings (e.g., SecurityConfig, EmailConfig) — add StripeConfig

### Integration Points
- `User.tier_id` FK — new column on existing User model, requires migration
- `UserProfileRead.tier_name` — replace hardcoded "free" with actual tier lookup
- Registration flow (`AuthService.register()`) — add auto-assign free tier logic
- `app/api/v1/` — new router files for tiers and billing endpoints

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose "ultra" as the top tier name instead of "enterprise" from REQUIREMENTS.md
- Rate limiting and usage limits are intentionally separated — rate limiting is anti-abuse (same for all), usage limits are business logic (tier-aware)
- Document limits are per-project, not per-account — allows users to distribute docs across projects
- Model access uses whitelist approach (array of allowed model slugs per tier) rather than credits/points system
- Stripe integration uses fully-hosted flows (Checkout Session + Customer Portal) — no custom payment UI in v1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-tier-system-permissions*
*Context gathered: 2026-04-11*
