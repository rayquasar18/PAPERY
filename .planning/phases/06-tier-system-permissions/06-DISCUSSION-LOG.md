# Phase 6: Tier System & Permissions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 06-tier-system-permissions
**Areas discussed:** Tier data model, Feature flag system, Rate limiting upgrade, Stripe billing scope

---

## Tier Data Model

### Q1: Cấu trúc bảng Tier nên lưu feature limits như thế nào?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated columns | Bảng `tier` với các cột riêng: max_projects, max_docs_per_project, etc. Dễ query, dễ validate. | |
| JSONB features column | Bảng `tier` với cột `features: JSONB`. Linh hoạt nhưng khó validate. | |
| Separate features table | Bảng `tier` + bảng `tier_feature` (tier_id, feature_key, value). Chuẩn hóa nhất. | |
| Hybrid | Core limits = dedicated columns, model whitelist + feature flags = JSONB. | ✓ |

**User's choice:** Asked "best practice của SaaS lớn?" → Hybrid approach recommended and accepted.
**Notes:** User wanted to follow best practices of large SaaS platforms (Stripe, Notion, Slack).

### Q2: Khi user mới đăng ký, xử lý tier như thế nào?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-assign free tier | Mỗi user mới tự động gán tier 'free'. Không có null case. | ✓ |
| Nullable with defaults | User mới = null tier, có bộ default permissions riêng. | |

**User's choice:** Auto-assign free (Recommended)

### Q3: Số lượng tier cố định hay dynamic?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 3 tiers | 3 tier cố định: free, pro, ultra. Admin chỉ chỉnh limits. | |
| Dynamic tiers | Admin có thể CRUD thêm tier mới. Linh hoạt cho custom plans. | ✓ |

**User's choice:** Dynamic tiers (Recommended)

### Q4: Limit document tính per project hay tổng trên toàn account?

| Option | Description | Selected |
|--------|-------------|----------|
| Per project | Limit document tính theo từng project. | ✓ |
| Tổng account | Limit document tính tổng trên toàn account. | |
| Cả hai | Có cả limit tổng account VÀ limit per project. | |

**User's choice:** Per project

### Q5: Limit model hoạt động theo kiểu nào?

| Option | Description | Selected |
|--------|-------------|----------|
| Whitelist models per tier | Mỗi tier có danh sách model được phép dùng. | ✓ |
| Model credits/points | Mỗi tier có X credits/tháng. Model mạnh tốn nhiều credits hơn. | |

**User's choice:** Whitelist models per tier

### Q6: Các limit có reset theo chu kỳ không?

| Option | Description | Selected |
|--------|-------------|----------|
| Monthly reset | Limit fix, limit document reset hàng tháng. | ✓ |
| Không reset | Limit là vĩnh viễn. | |
| Tuỳ loại limit | Một số limit reset monthly, một số không. | |

**User's choice:** Monthly reset (Recommended)

### Q7: Ngoài 4 loại limit, còn loại nào nữa?

| Option | Description | Selected |
|--------|-------------|----------|
| 4 loại đủ rồi | project, document, fix, model. | |
| Thêm file size limit | Giới hạn kích thước file upload per tier. | ✓ |
| Thêm storage quota | Tổng dung lượng lưu trữ per tier. | |

**User's choice:** Thêm file size limit

---

## Feature Flag System

### Q1: Cách check feature permission ở runtime?

| Option | Description | Selected |
|--------|-------------|----------|
| Dependency injection | FastAPI Depends(require_feature('can_export_pdf')). Nhất quán với pattern hiện tại. | ✓ |
| Decorator pattern | @require_tier('pro') trên route function. | |
| Middleware global | Middleware check mọi request, map route → required tier. | |

**User's choice:** Dependency injection (Recommended)

### Q2: Tier data có cần cache không?

| Option | Description | Selected |
|--------|-------------|----------|
| No cache | Load tier data từ DB mỗi request. | |
| Redis cache + TTL | Cache tier data trong Redis với TTL 5 phút. Invalidate khi tier thay đổi. | ✓ |
| In-memory cache | Load tier data vào memory khi app start. | |

**User's choice:** Asked "SaaS dùng cách nào tốt nhất?" → Redis cache + TTL recommended and accepted.

### Q3: Khi user upgrade/downgrade, permissions cập nhật khi nào?

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate | Permissions cập nhật ngay lập tức, request tiếp theo đã dùng tier mới. | ✓ |
| End of billing cycle | Permissions cập nhật sau billing cycle kết thúc. | |

**User's choice:** Immediate (Recommended)

---

## Rate Limiting Upgrade

### Critical Clarification

**User clarified:** "tier không rate limit request, chỉ rate limit để chống tấn công thôi, còn limit là limit các vấn đề khác"

This reframed the entire area:
- **Rate limiting** (anti-abuse) = same for all users, not tier-aware
- **Usage limits** (business logic) = tier-aware quotas (projects, docs, fixes, models, file size)
- TIER-03 requirement maps to usage limits, not traditional rate limiting

### Q1: Rate limiting giữ như cũ, chỉ tập trung usage limits cho tier?

| Option | Description | Selected |
|--------|-------------|----------|
| Giữ rate limit như cũ | Rate limiting (chống spam) giữ nguyên. Tập trung Phase 6 vào usage limits. | ✓ |
| Nâng cao rate limit theo tier | Pro/ultra được rate limit cao hơn. | |

**User's choice:** Giữ rate limit như cũ (Recommended)

### Q2: Usage limits check ở đâu?

| Option | Description | Selected |
|--------|-------------|----------|
| Dependency injection | Depends(check_usage('documents')) trước action. | ✓ |
| Service layer check | Check trong service layer (business logic). | |

**User's choice:** Dependency injection (Recommended)

### Q3: Tracking usage lưu ở đâu?

| Option | Description | Selected |
|--------|-------------|----------|
| DB tracking table | Bảng usage_tracking (user_id, metric, count, period_start, period_end). | ✓ |
| Redis counters | Redis counters với TTL = billing period. | |
| COUNT from source tables | Count trực tiếp từ bảng gốc. | |

**User's choice:** DB tracking table (Recommended)

---

## Stripe Billing Scope

### Q1: Flow thanh toán Stripe?

| Option | Description | Selected |
|--------|-------------|----------|
| Checkout Session | Redirect user sang trang thanh toán Stripe hosted. | ✓ |
| Stripe Elements | Embed form thanh toán vào frontend. | |
| Hybrid | Checkout cho subscribe, Elements cho update card. | |

**User's choice:** Checkout Session (Recommended)

### Q2: Quản lý subscription?

| Option | Description | Selected |
|--------|-------------|----------|
| Stripe Portal | Stripe Customer Portal — user tự quản lý subscription. Stripe host hoàn toàn. | ✓ |
| Custom billing UI | Build billing UI riêng trong PAPERY. | |

**User's choice:** Stripe Portal (Recommended)

### Q3: Webhook events nào cần handle?

| Option | Description | Selected |
|--------|-------------|----------|
| Core events only | 4 events cốt lõi: checkout.session.completed, subscription.updated/deleted, invoice.payment_failed | |
| Full event coverage | Tất cả events + invoice.paid, customer.updated, payment_method.attached | ✓ |

**User's choice:** Full event coverage

### Q4: Testing Stripe trong development?

| Option | Description | Selected |
|--------|-------------|----------|
| Stripe test mode | Stripe test API keys cho development/staging. | ✓ |
| Mock Stripe locally | Mock Stripe hoàn toàn, không cần Stripe account. | |

**User's choice:** Stripe test mode (Recommended)

---

## Claude's Discretion

- Exact Redis TTL duration for tier cache
- Stripe webhook endpoint path and retry handling
- Usage tracking table schema details
- Migration strategy for tier_id FK on User model

## Deferred Ideas

None — discussion stayed within phase scope
