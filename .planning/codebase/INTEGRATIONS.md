# INTEGRATIONS.md — External APIs & Integrations

> **Status:** Pre-development (scaffold phase)
> Last updated: 2026-04-01

PAPERY is currently in the scaffold/planning stage. No integration code has been written. This document captures **confirmed signals** from project files and **planned/required integrations** derived from the feature set described in `README.md` and `CLAUDE.md`.

---

## 1. Confirmed Integrations (Signal-Based)

### 1.1 AI / LLM Providers
**Signal:** `CLAUDE.md` describes multi-agent research workflows, Q&A with citation, multi-language translation, and insight generation — all requiring LLM access. Planning config (`.planning/config.json`) uses `opus` and `sonnet` model profiles, directly indicating Anthropic as a planned provider.

| Provider | Evidence | Use Case |
|---|---|---|
| **Anthropic (Claude)** | `config.json` uses `opus`/`sonnet` profiles | LLM inference, multi-agent workflows |
| **OpenAI** | Standard for embeddings + LLM; expected | LLM fallback, embeddings |
| **Google (Gemini)** | Multi-provider expected per feature scope | LLM alternative |
| **Groq / Mistral / DeepSeek** | Likely as optional providers | LLM speed/cost optimization |
| **Ollama (local)** | Privacy-first use case; likely optional | Local/offline LLM |

**Decision pending:** Whether to use provider SDKs directly or a unified abstraction layer (e.g., LangChain, LiteLLM, Esperanto).

---

### 1.2 Database
**Signal:** `.gitignore` includes `db.sqlite3` (SQLite), `migrations/versions/` (Alembic), and `local_settings.py` (Django-style) patterns.

| Database | Evidence | Role |
|---|---|---|
| **Relational DB** (PostgreSQL likely) | `migrations/versions/` → Alembic | Primary data store: users, documents, sessions |
| **SQLite** | `db.sqlite3` in `.gitignore` | Development / local fallback |
| **Vector Store** (TBD) | Required for semantic Q&A + cross-doc search | Embedding storage and similarity search |

**Open decisions:**
- PostgreSQL + pgvector vs dedicated vector DB (Qdrant, Weaviate, Chroma, Pinecone)
- SurrealDB as combined graph + vector store (reference pattern observed)

---

### 1.3 Task Queue
**Signal:** `celerybeat-schedule` and `celerybeat.pid` in `.gitignore`.

| Service | Evidence | Role |
|---|---|---|
| **Celery** | `.gitignore` confirms Celery beat scheduler | Async document processing, AI pipeline jobs |
| **Redis / RabbitMQ** | Standard Celery broker (not confirmed yet) | Message broker for task queue |

---

### 1.4 File Storage
**Signal:** Feature set requires storing uploaded documents (PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown).

| Service | Evidence | Role |
|---|---|---|
| **Local filesystem** | Expected for development | Document storage |
| **S3-compatible** (AWS S3 / R2 / MinIO) | Standard for production doc platforms | Production document/asset storage |

**Decision pending.**

---

### 1.5 Deployment / Hosting
**Signal:** `.vercel` in `.gitignore` indicates Vercel as a potential frontend deployment target.

| Service | Evidence | Role |
|---|---|---|
| **Vercel** | `.vercel` in `.gitignore` | Frontend (Next.js) deployment |
| **Container runtime** | Standard for Python APIs | Backend API hosting |

---

## 2. Planned Integrations (Feature-Derived)

These integrations are **required** by features described in `README.md` and `CLAUDE.md` but have not yet been designed or implemented.

### 2.1 Document Processing
| Library / Service | Purpose | Required Feature |
|---|---|---|
| **pdfplumber / PyMuPDF / pdfminer** | PDF text + layout extraction | Universal document support (PDF) |
| **python-docx** | DOCX parsing | Universal document support (DOCX) |
| **openpyxl / pandas** | XLSX/CSV parsing | Universal document support (XLSX, CSV) |
| **python-pptx** | PPTX parsing | Universal document support (PPTX) |
| **Tesseract / Surya / cloud OCR** | Scanned PDF support | Intelligent Q&A on scanned docs |
| **Unstructured.io** | All-in-one document parsing | Possible unified extraction layer |

### 2.2 AI / Embedding Pipeline
| Service | Purpose | Required Feature |
|---|---|---|
| **OpenAI Embeddings** or **Cohere** | Text vectorization | Semantic Q&A, cross-doc search |
| **LangChain / LangGraph** | LLM orchestration, agents | Multi-agent research workflows |
| **Chunking strategy** | Document splitting | Q&A accuracy, citation precision |

### 2.3 Translation
| Service | Purpose | Required Feature |
|---|---|---|
| **LLM-based translation** | Structure-preserving translation | Multi-language document translation |
| **DeepL API** (optional) | High-quality document translation | Alternative to LLM translation |
| **Google Cloud Translation** (optional) | Broad language coverage | Multi-language support |

### 2.4 Authentication
| Service | Purpose | Notes |
|---|---|---|
| **Auth system (TBD)** | User authentication + authorization | Required for multi-user platform |
| Options: Clerk, Auth.js, Supabase Auth, custom JWT | — | Decision pending |

### 2.5 Search & Vector Retrieval
| Service | Purpose | Required Feature |
|---|---|---|
| **Vector DB** (pgvector / Qdrant / Weaviate / Chroma) | Semantic similarity search | Q&A, cross-doc analysis, knowledge graph |
| **Full-text search** (PostgreSQL FTS / Elasticsearch) | Keyword search | Document and note search |

### 2.6 Template Marketplace
| Service | Purpose | Required Feature |
|---|---|---|
| **Community template store** | Template hosting + distribution | Marketplace for community templates |
| **Format renderers** (Pandoc, WeasyPrint, etc.) | Document output generation | Formatted report / document generation |

### 2.7 Citation Export
| Library | Purpose | Required Feature |
|---|---|---|
| **citeproc-py / pybtex** | Academic citation formatting | Export citations in standard formats |
| **Citation formats** | APA, MLA, Chicago, BibTeX | Citation & reference feature |

---

## 3. Third-Party Services Matrix

| Category | Service | Status | Priority |
|---|---|---|---|
| LLM — Anthropic | Claude (Opus, Sonnet, Haiku) | Planned | P0 |
| LLM — OpenAI | GPT-4o, o-series | Planned | P0 |
| LLM — Local | Ollama | Optional | P2 |
| Embeddings | OpenAI / Cohere | Planned | P0 |
| Database | PostgreSQL | Planned | P0 |
| Vector Store | pgvector or Qdrant | Planned | P0 |
| Task Queue | Celery + Redis | Planned | P1 |
| File Storage | Local / S3-compatible | Planned | P1 |
| Auth | TBD | Planned | P0 |
| Deployment (Frontend) | Vercel | Optional | P2 |
| Translation | LLM / DeepL | Planned | P1 |
| Document Parsing | pdfplumber, python-docx, etc. | Planned | P0 |
| OCR | Tesseract / cloud | Optional | P2 |

---

## 4. Security Considerations

From `CLAUDE.md` security rules:

- All API keys stored as environment variables (`.env` files, gitignored)
- Never commit secrets, credentials, or `.env` files
- Production deployments must use a secure secrets manager (AWS Secrets Manager, Doppler, etc.)
- Auth system must be hardened before any public deployment

---

## 5. Open Integration Decisions

- [ ] LLM abstraction: Direct provider SDKs vs LangChain vs LiteLLM vs custom
- [ ] Embedding provider: OpenAI vs Cohere vs local (sentence-transformers)
- [ ] Vector store: pgvector (simple) vs Qdrant / Weaviate (dedicated)
- [ ] Auth provider: Clerk vs Auth.js vs Supabase vs custom JWT
- [ ] File storage: Local + S3 vs object storage service
- [ ] Translation approach: LLM-only vs hybrid (LLM + DeepL)
- [ ] Citation export: Library vs custom renderer
- [ ] Marketplace backend: Simple DB vs dedicated content delivery

---

*This document reflects the scaffold state of the project. Update as integrations are designed and implemented.*
