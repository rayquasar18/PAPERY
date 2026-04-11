# Phase 9: Frontend Foundation & Auth UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 09-frontend-foundation-auth-ui
**Areas discussed:** Layout & Navigation, Auth Pages & UX Flow, Theme & Design Foundation, i18n & Routing Strategy, Tech Stack & Libraries

---

## Layout & Navigation

### Layout Style

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar + Header | Sidebar cố định bên trái, top header với user menu. Giống ChatGPT, Notion. | |
| Top Nav Only | Navigation bar cố định trên cùng, không sidebar. | |
| Hybrid (Sidebar + Top Bar) | Kết hợp cả hai: sidebar cho workspace/project context, top bar cho global actions. Giống Slack, Linear. | ✓ |

**User's choice:** Hybrid (Sidebar + Top Bar)
**Notes:** User also mentioned chat panel should be on the right side. Main content area should support split view (2-3 panes) for file comparison.

### Chat Panel Position

| Option | Description | Selected |
|--------|-------------|----------|
| Right panel (co giãn) | Panel chat cố định bên phải, có thể resize. Giống Cursor AI chat. | ✓ |
| Trang riêng (/chat) | Chat là một trang riêng, full screen. Giống ChatGPT. | |
| Hybrid (page + floating panel) | Cả hai: chat page riêng + mini chat panel ở bất kỳ trang nào. | |

**User's choice:** Right panel (co giãn)
**Notes:** User specified main content can also be split into multiple panes for file comparison.

### Sidebar Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsible (icon-only khi thu) | Sidebar co lại chỉ còn icon khi user click nút toggle. Giống VS Code, Linear. | ✓ |
| Always expanded | Sidebar luôn mở với full width. | |
| Responsive auto-collapse | Sidebar tự động thu/mở theo width màn hình. | |

**User's choice:** Collapsible (icon-only khi thu)

### Mobile Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar ẩn + Bottom Nav | Sidebar biến mất, thay bằng bottom nav. | |
| Hamburger menu only | Chỉ hamburger menu. | |
| Icon-only mini sidebar | Sidebar thu nhỏ thành icon strip. | |
| Other | Sidebar biến mất, icon đóng/mở ở header, theo shadcn/ui dashboard-01 | ✓ |

**User's choice:** Sidebar ẩn, icon đóng/mở ở header (NOT hamburger). Reference: `npx shadcn@latest add dashboard-01`

---

## Auth Pages & UX Flow

### Auth Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Centered card | Form login/register ở giữa trang với background gradient. | |
| Split screen (image + form) | Chia đôi: bên trái là hình ảnh/branding, bên phải là form. Giống Clerk, Auth0. | ✓ |
| Full-width minimal | Form chiếm full width, không card. | |

**User's choice:** Split screen (image + form)

### Post-Login Redirect

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard (danh sách projects) | Sau login → vào thẳng dashboard hiển danh sách projects. | ✓ |
| Project gần nhất | Vào project cuối cùng đang mở. | |
| Trang Home (quick actions) | Trang welcome với quick actions. | |

**User's choice:** Dashboard (danh sách projects)

### OAuth Position

| Option | Description | Selected |
|--------|-------------|----------|
| Dưới form + divider | Nút Google và GitHub nằm dưới form email/password, ngăn cách bởi divider "or". | ✓ |
| Trên form (OAuth ưu tiên) | OAuth buttons trước form, ưu tiên social login. | |

**User's choice:** Dưới form + divider

### Error Display

| Option | Description | Selected |
|--------|-------------|----------|
| Inline dưới field | Lỗi hiển ngay dưới field liên quan, màu đỏ. Real-time validation khi blur. | ✓ |
| Toast/Alert ở đầu form | Lỗi hiện ở đầu form dạng alert/toast. | |

**User's choice:** Inline dưới field

---

## Theme & Design Foundation

### Color Palette

| Option | Description | Selected |
|--------|-------------|----------|
| Blue/Indigo professional | Tông xanh/tím hiện đại, chuyên nghiệp. Giống Notion, Linear. | ✓ |
| Green/Teal fresh | Tông xanh lá tươi mới, thân thiện. | |
| Orange/Amber warm | Tông cam/vàng năng động, nổi bật. | |

**User's choice:** Blue/Indigo professional

### Typography

| Option | Description | Selected |
|--------|-------------|----------|
| Inter | Font phổ biến nhất cho SaaS/dashboard. Mặc định của shadcn/ui. | ✓ |
| Geist (Vercel font) | Font của Vercel, hiện đại, monospace variant cho code. | |
| System fonts | System font stack. Nhanh nhất, không cần load font. | |

**User's choice:** Inter

### Dark Mode Toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle trên header | User chọn qua toggle trên top bar. 3 options: light, dark, system. Persist localStorage + cookie. | ✓ |
| System default + Settings override | Mặc định theo system, override trong Settings. | |

**User's choice:** Toggle trên header

---

## i18n & Routing Strategy

### Default Locale

| Option | Description | Selected |
|--------|-------------|----------|
| English default | Tiếng Anh mặc định. Phổ biến cho SaaS quốc tế. | ✓ |
| Vietnamese default | Tiếng Việt mặc định. | |

**User's choice:** English default

### URL Locale Prefix

| Option | Description | Selected |
|--------|-------------|----------|
| Prefix bắt buộc (/en/, /vi/) | Mọi URL đều có locale prefix. Chuẩn SEO, dễ routing. | ✓ |
| Default ẩn prefix | Default locale không có prefix, chỉ non-default mới có. | |

**User's choice:** Prefix bắt buộc

### Auto-Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-detect + switch | Đọc browser Accept-Language, redirect về locale phù hợp. User có thể switch sau. | ✓ |
| Không auto-detect | Luôn English, user tự chuyển. | |

**User's choice:** Auto-detect + switch

---

## Tech Stack & Libraries

### HTTP Client

| Option | Description | Selected |
|--------|-------------|----------|
| Axios | Interceptors mạnh, auto-transform JSON. Thư viện phổ biến nhất. | ✓ |
| ky (fetch wrapper) | Wrapper nhẹ trên fetch(), hỗ trợ retry, hooks. | |
| Native fetch | Không dependency nhưng cần viết nhiều hơn. | |

**User's choice:** Axios

### Form Management

| Option | Description | Selected |
|--------|-------------|----------|
| React Hook Form + Zod | Performant, nhẹ, TypeScript-first. Kết hợp Zod validation. | ✓ |
| Formik + Yup | Lâu đời hơn nhưng nặng hơn, re-render nhiều hơn. | |

**User's choice:** React Hook Form + Zod

### Server State

| Option | Description | Selected |
|--------|-------------|----------|
| TanStack Query v5 | Caching, background refetch, mutations, devtools. Chuẩn cho server state. | ✓ |
| SWR (Vercel) | Nhẹ hơn, đơn giản hơn. Thiếu mutation support bằng TanStack. | |

**User's choice:** TanStack Query v5

### Additional Libraries

| Option | Description | Selected |
|--------|-------------|----------|
| sonner (toast) | Toast notifications hiện đại, animated, stackable. | ✓ |
| nuqs (URL state) | Type-safe URL search params state management cho Next.js. | ✓ |
| next-themes | Theme provider cho Next.js với SSR support, system detection. | ✓ |
| date-fns | Tree-shakeable, functional API cho date formatting. | ✓ |

**User's choice:** All four selected

### Package Manager

| Option | Description | Selected |
|--------|-------------|----------|
| pnpm | Nhanh, tiết kiệm disk (hard links), strict dependencies. | ✓ |
| npm | Built-in, không cần cài thêm. | |
| bun | Runtime + package manager, nhanh nhất. Còn mới. | |
| yarn berry | PnP mode, mạnh cho monorepo. | |

**User's choice:** pnpm

### Date Library

| Option | Description | Selected |
|--------|-------------|----------|
| date-fns v4 | Tree-shakeable, functional API. Import từng function, bundle nhỏ. | ✓ |
| dayjs | API giống moment.js, rất nhẹ (2KB). Plugin system. | |

**User's choice:** date-fns

### Animation

| Option | Description | Selected |
|--------|-------------|----------|
| framer-motion | Animation library phổ biến nhất cho React. | |
| CSS/Tailwind only | Chỉ dùng Tailwind CSS transitions + shadcn/ui built-in animations. | ✓ |
| react-spring | Physics-based animations. | |

**User's choice:** Tailwind CSS only — no additional animation library for v1

---

## Claude's Discretion

- Component file structure within `src/` — Claude decides based on Next.js 16 best practices
- Exact Tailwind color values for Blue/Indigo palette
- shadcn/ui component list to install initially
- Breakpoint values for responsive design
- Zustand store structure
- Split-view implementation approach

## Deferred Ideas

None — discussion stayed within phase scope
