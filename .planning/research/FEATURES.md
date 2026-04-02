# Features Research — PAPERY

> AI-Powered Document Intelligence SaaS Platform
> Research date: 2026-04-01

---

## 1. Feature Categories

### 1.1 Table Stakes — SaaS Foundation (Must Have)

Users expect these from any modern SaaS. Missing any = users leave.

| Feature | Complexity | Dependencies | Notes |
|---------|-----------|--------------|-------|
| **Email/password registration** | Low | SMTP service | Email verification required |
| **Login/logout** | Low | JWT, Redis | Access + refresh token rotation |
| **Password reset** | Low | SMTP, token system | Secure time-limited links |
| **OAuth login (Google)** | Medium | Google OAuth API | Most common social login |
| **User profile** | Low | Auth system | View/edit own profile |
| **Admin dashboard** | Medium | Auth + role system | User management, system config |
| **Role-based access control** | Medium | User model, middleware | Admin vs regular user minimum |
| **Tier/subscription system** | Medium | User model, tier model | Free/pro/enterprise differentiation |
| **Rate limiting** | Medium | Redis, tier system | Per-endpoint, tier-aware limits |
| **Project/workspace CRUD** | Low | Auth, ACL | Create, organize, share workspaces |
| **Resource-level permissions (ACL)** | Medium | ACL model, middleware | Per-resource owner/viewer/editor |
| **Responsive UI** | Medium | Tailwind, shadcn/ui | Mobile + desktop layouts |
| **Dark/light theme** | Low | Theme context | User preference persistence |
| **Internationalization (i18n)** | Medium | next-intl | At minimum EN + VI |
| **Error handling (structured)** | Low | Exception hierarchy | Consistent API error format |
| **API versioning** | Low | Router structure | /api/v1/ prefix pattern |
| **Health check endpoint** | Low | — | Infrastructure monitoring |
| **CORS configuration** | Low | Middleware | Frontend ↔ backend communication |
| **Environment-based config** | Low | Pydantic Settings | Dev/staging/production profiles |

### 1.2 Table Stakes — Document Platform (v2, after SaaS base)

| Feature | Complexity | Dependencies | Notes |
|---------|-----------|--------------|-------|
| **Document upload** | Medium | MinIO, file validation | Multi-format support |
| **Document viewer** | High | PDF.js, custom renderers | In-app rendering per format |
| **Document listing/management** | Low | Project system, ACL | Browse, search, organize |
| **AI Q&A with citations** | High | QuasarFlow API, embeddings | Core value proposition |
| **Document summarization** | Medium | QuasarFlow API | Auto-extract key points |
| **Search across documents** | Medium | Full-text search, embeddings | Within project scope |

### 1.3 Differentiators (Competitive Advantage)

| Feature | Complexity | Dependencies | Notes |
|---------|-----------|--------------|-------|
| **AI document editing (visual + chat)** | Very High | Editor framework, QuasarFlow | PAPERY's key differentiator |
| **Structure-preserving translation** | Very High | QuasarFlow, doc parser | Unique — most tools lose formatting |
| **Multi-agent research workflows** | Very High | QuasarFlow multi-agent | End-to-end research → report |
| **Template system + doc generation** | High | Template engine, QuasarFlow | Custom output formats |
| **Cross-document analysis** | High | QuasarFlow, vector search | Find patterns, contradictions |
| **Interactive citation panel** | Medium | Document viewer, citation index | Click citation → jump to source |
| **Knowledge graph visualization** | Very High | Graph DB or embeddings | Topic clustering, connections |

### 1.4 Anti-Features (Deliberately NOT Build)

| Feature | Reason |
|---------|--------|
| **Real-time collaborative editing (Google Docs-style)** | Extremely complex (CRDT/OT), not core value. Single-user-at-a-time is fine for v1-v2 |
| **Built-in LLM hosting** | QuasarFlow handles AI. Don't embed LLM logic in PAPERY |
| **Mobile native app** | Web-first, responsive design covers mobile use cases |
| **Offline mode** | Document AI requires internet. Don't over-engineer offline sync |
| **Blockchain/Web3 anything** | No use case, adds complexity |
| **Built-in billing/payment** | Use Stripe integration when needed, don't build payment processor |
| **Social features (comments, likes, followers)** | Not a social platform. Share via project ACL |
| **Version control for documents** | Complex, low ROI for v1. Simple undo/redo is sufficient |

---

## 2. Feature Dependencies

```
Auth System
  └── Tier System
       └── Rate Limiting
  └── ACL System
       └── Project System
            └── Document Upload
                 └── Document Viewer
                      └── AI Q&A (needs QuasarFlow)
                           └── Citation Panel
                           └── Summarization
                      └── AI Document Editing (needs QuasarFlow)
                           └── Translation
                 └── Search
                      └── Cross-document Analysis
```

---

## 3. Competitive Landscape

| Platform | Strengths | Weaknesses | PAPERY Opportunity |
|----------|-----------|------------|-------------------|
| **Google NotebookLM** | Polished UI, Google's AI, audio generation | Closed-source, no editing, Google lock-in | Open-source, direct editing, self-hostable |
| **Open Notebook** | Open-source, multi-provider LLM | No document editing, simpler UI | Editing + translation + better SaaS features |
| **Dify** | Workflow builder, multi-model | Not document-focused, complex setup | Document-native, simpler UX |
| **Quivr** | RAG-focused, open-source | No editing, limited document types | Full document lifecycle |

---

## 4. v1 Scope Recommendation

**v1 = SaaS Foundation (table stakes section 1.1)**

Ship a rock-solid SaaS base:
- Complete auth system with tiers and permissions
- Admin panel for user/tier management
- Project system with ACL
- Infrastructure ready for document features
- QuasarFlow integration interface (stub/mock)

**Why:** Every feature above depends on auth + projects + infrastructure. Building this wrong means rebuilding everything later.

---

*Research based on competitive analysis, SaaS best practices, and PAPERY's positioning as an AI document intelligence platform.*
