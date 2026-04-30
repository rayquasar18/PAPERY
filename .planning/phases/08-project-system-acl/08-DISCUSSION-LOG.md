# Phase 8: Project System & ACL - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 08-project-system-acl
**Areas discussed:** ACL quyền truy cập, Project lifecycle, Invite & membership, Danh sách & tìm kiếm project

---

## ACL quyền truy cập

| Option | Description | Selected |
|--------|-------------|----------|
| Owner-only quản trị | Owner full quyền + quản lý member; Editor sửa nội dung; Viewer chỉ đọc | ✓ |
| Editor quản lý member | Owner và Editor cùng quản lý member | |
| Tối giản 2 role | Chỉ owner + member | |

**User's choice:** Owner-only quản trị.
**Notes:** Giữ ma trận quyền rõ ràng, hạn chế xung đột quản trị.

---

## Project lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Soft delete + không restore | Owner xóa thì ẩn khỏi list ngay, chưa có restore API trong phase này | ✓ |
| Soft delete + restore trong phase | Có thêm restore endpoint trong grace period | |
| Hard delete | Xóa vĩnh viễn | |

**User's choice:** Soft delete + không restore.
**Notes:** Giữ scope gọn, theo pattern soft delete hiện tại.

---

## Invite & membership

| Option | Description | Selected |
|--------|-------------|----------|
| Link + email, expiry 7 ngày | Hỗ trợ cả invite link và email, role gán lúc tạo invite | ✓ |
| Chỉ invite link | Giảm phụ thuộc email service | |
| Chỉ email invite | Quản trị invite qua email thuần | |

**User's choice:** Link + email, expiry 7 ngày.
**Notes:** Cần cả tiện lợi (link) và mời trực tiếp (email).

---

## Danh sách & tìm kiếm project

| Option | Description | Selected |
|--------|-------------|----------|
| Owned + Shared tách loại | Một endpoint list chung, item có relationship_type, search name, sort updated_at desc | ✓ |
| Hai endpoint tách riêng | /owned và /shared riêng | |
| List chung tối giản | Không phân biệt owned/shared | |

**User's choice:** Owned + Shared tách loại.
**Notes:** Tối ưu cho FE khi cần render theo quan hệ sở hữu/chia sẻ.

---

## Claude's Discretion

- Chi tiết schema invite token/accept payload.
- Bố cục dependency/service/repository cho ACL enforcement.
- Mặc định phân trang và giới hạn page size.

## Deferred Ideas

- Restore API sau soft delete được defer sang phase sau.
