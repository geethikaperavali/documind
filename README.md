# DocuMind – Unified AI Document & Authoritative Intelligence Platform

DocuMind is an enterprise-grade AI document intelligence platform built with vanilla HTML5/CSS3/JavaScript on the frontend, Python FastAPI on the backend, Supabase (PostgreSQL, Auth, Storage, pgvector) for data storage and vector search, and Google Gemini API + Sentence Transformers for Retrieval-Augmented Generation (RAG) and multi-domain authoritative intelligence.

---

## 🌟 Workspaces & Core Capabilities

DocuMind is organized into a modular workspace suite designed for analysts, researchers, and enterprise knowledge workers:

### 1. Workspace Dashboard
- **Live System Analytics**: Real-time database metrics for total indexed documents, total storage consumption, and queries executed.
- **Recent Intelligence Index**: Fast access to recently uploaded documents with status indicators, chunk breakdown, and file sizes.
- **Audit Activity Feed**: Chronological trail of user ingestions, analysis tasks, and query interactions.

### 2. Knowledge Base (Document Management)
- **Multi-Format Extraction**: Deep parsing and semantic chunking for **PDF** (PyMuPDF / pypdf), **Word (DOCX)** (python-docx), and **TXT** files.
- **Drag-and-Drop Ingestion**: Interactive drag-and-drop dropzone with validation (files up to 25 MB).
- **Tenant Data Isolation**: Every document and vector chunk is strictly partitioned by authenticated user ID via Supabase Row Level Security (RLS).
- **Chunk Inspector**: Live modal to review extracted text chunks, page offsets, and chunk metadata.
- **Cascading Deletion**: Clean removal of Supabase Storage objects, relational records, and vector embeddings.

### 3. AI Assistant (RAG Intelligence)
- **Dense Vector Search**: Semantic similarity matching using 384-dimensional embeddings (`all-MiniLM-L6-v2`) and pgvector cosine distance.
- **Strict Grounding**: Prompt engineering to prevent hallucinations and strictly ground answers in retrieved document context.
- **Transparent Citations**: Every generated response attributes quotes with exact document titles, page numbers, similarity metrics, and text snippets.
- **Multi-Turn Thread Memory**: Conversational context retention across threads with seamless session clearing.

### 4. Research Studio
- **Universal Multi-Domain Grounding**: Deep search and intelligence synthesis across 6 domains:
  - *AI & ML Models* (Model benchmarks, release papers, evaluation metrics)
  - *Law & Gazettes* (Acts, statutory notifications, regulatory mandates)
  - *Finance & Markets* (Macroeconomic data, central bank policies, quarterly filings)
  - *Healthcare & FDA* (Clinical trials, drug approvals, regulatory standards)
  - *Academic (arXiv)* (Scientific preprints, citations, methodology breakdowns)
  - *Cybersecurity & CVE* (Vulnerability registries, advisory briefs, threat intelligence)
- **Configurable Investigation Depths**: Brief Executive Overview, Comprehensive Dossier, or Regulatory & Statutory Scan.
- **Source Registry**: Verified authoritative registry ensuring grounded synthesis from primary sources.

### 5. Compare & Verify
- **Cross-Document Entity Comparison**: Side-by-side analysis of multiple uploaded contracts, policies, or technical papers.
- **Contradiction Discovery**: Identifies discrepancies, altered clauses, and conflicting factual claims across document versions.
- **Alignment Metrics**: Quantitative compatibility scores and clause-by-clause diff tracking.

### 6. Knowledge Explorer
- **Interactive Concept Graph**: Semantic graph representation of interrelated topics, extracted entities, and document themes.
- **Entity Linking & Clustering**: Discovers latent connections between isolated documents in the knowledge base.

### 7. Action Studio
- **Operational Task Extraction**: Converts dense reports into structured, assignable action items.
- **Decision Matrix & Executive Briefs**: Generates structured executive summaries, risk tables, and compliance checklists.

### 8. Live Monitor
- **Scheduled Source Feeds**: Continuous surveillance of regulatory updates, arXiv releases, and industry publications.
- **Alert Dispatch**: Configurable notification triggers for keyword matches and policy revisions.

### 9. Account & Security Settings
- **Profile Management**: Update full name, view account identifiers, and manage preferences.
- **Security & Session Controls**: Review session status, active credentials, and perform secure sign-out.

---

## 🏗️ Project Architecture

```
documind/
├── backend/
│   ├── main.py                     # FastAPI application entrypoint & static mounting
│   ├── config.py                   # Pydantic environment configuration & settings
│   ├── auth.py                     # Supabase JWT verification & get_current_user dependency
│   ├── database.py                 # Supabase client factories (Admin & User clients)
│   ├── port_3000_forwarder.py      # Local OAuth redirect forwarder (Port 3000 -> 8000)
│   ├── routers/
│   │   ├── auth_router.py          # /api/auth: /me profile and public /config
│   │   ├── chat_router.py          # /api/chat: RAG Q&A, thread management
│   │   ├── documents_router.py     # /api/documents: File ingestion, chunk inspection, deletion
│   │   ├── dashboard_router.py     # /api/dashboard: Real-time metrics & activity
│   │   ├── profile_router.py       # /api/profile: Profile updating & preferences
│   │   ├── research_router.py      # /api/research: Multi-domain research synthesis
│   │   ├── compare_router.py       # /api/compare: Cross-document comparison & verification
│   │   ├── explorer_router.py      # /api/explorer: Concept graph discovery & relations
│   │   ├── action_router.py        # /api/actions: Action item extraction & briefs
│   │   ├── monitor_router.py       # /api/monitor: Surveillance feeds & monitoring
│   │   └── temporal_router.py      # /api/temporal: Timeline & historical trend tracking
│   └── services/
│       ├── document_processor.py   # PDF, DOCX, and TXT parsing & chunking
│       ├── embedding_service.py    # Local sentence-transformers dense vector generator
│       ├── rag_service.py          # Vector similarity retrieval & Gemini synthesis
│       ├── storage_service.py      # Supabase Storage management
│       ├── search_service.py       # Web grounding & primary source retrieval (bs4, DuckDuckGo)
│       ├── gemini_gateway.py       # Centralized Google Gemini API interface
│       ├── orchestrator.py         # Multi-agent coordination across intelligence studios
│       ├── research_service.py     # Research synthesis engine
│       ├── compare_service.py      # Verification and clause-comparison logic
│       ├── explorer_service.py     # Graph entity mapping
│       ├── action_service.py       # Executive summary & action extraction logic
│       ├── monitor_service.py      # Source monitoring engine
│       ├── surveillance_scheduler.py # Background periodic surveillance tasks
│       ├── temporal_intelligence.py# Time-series analysis engine
│       ├── source_registry.py      # Verified primary source registry
│       └── ai_intelligence.py      # Shared AI prompt utilities
├── frontend/
│   ├── index.html                  # Main Dashboard
│   ├── documents.html              # Knowledge Base
│   ├── chat.html                   # AI Assistant
│   ├── research.html               # Research Studio
│   ├── compare.html                # Compare & Verify
│   ├── explorer.html               # Knowledge Explorer
│   ├── action.html                 # Action Studio
│   ├── monitor.html                # Live Monitor
│   ├── settings.html               # Account Settings
│   ├── login.html                  # Authentication: Sign In
│   ├── signup.html                 # Authentication: Sign Up
│   ├── forgot-password.html        # Authentication: Password Recovery
│   ├── reset-password.html         # Authentication: Password Reset
│   ├── css/
│   │   ├── main.css                # Core design system, layout, buttons, badges
│   │   ├── auth.css                # Authentication cards & form styling
│   │   ├── chat.css                # AI chat interface, citations & typing indicator
│   │   ├── documents.css           # Dropzone, chunk inspector modal, tables
│   │   └── studios.css             # Intelligence studios layout & studio card styles
│   └── js/
│       ├── config.js               # Frontend environment & route definitions
│       ├── auth.js                 # Supabase client manager & route guards
│       ├── api.js                  # Authenticated HTTP fetch wrapper (auto JWT Bearer)
│       ├── loader.js               # Branded application loading experience
│       ├── dashboard.js            # Dashboard view controller
│       ├── documents.js            # Knowledge Base view controller
│       ├── chat.js                 # AI Assistant view controller
│       ├── research.js             # Research Studio controller
│       ├── compare.js              # Compare & Verify controller
│       ├── explorer.js             # Knowledge Explorer controller
│       ├── action.js               # Action Studio controller
│       ├── monitor.js              # Live Monitor controller
│       └── settings.js             # Account settings controller
├── database/
│   └── migrations.sql              # Supabase schema, pgvector, storage buckets & RLS policies
├── scripts/
│   ├── e2e_full_verification.py    # Automated end-to-end regression & studio test suite
│   └── test_ai_assistant_routing.py # Isolated AI Assistant intent routing test harness
├── .env.example                    # Environment variable template
├── requirements.txt                # Python project dependencies
└── README.md                       # Documentation & setup guide
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- **Python 3.10+**
- A **[Supabase](https://supabase.com)** account (Free tier supported)
- A **[Google AI Studio](https://aistudio.google.com/app/apikey)** API key for Gemini

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-username/documind.git
cd documind

# Create a clean virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup in Supabase
1. Create a new project in your [Supabase Dashboard](https://supabase.com/dashboard).
2. Open the **SQL Editor** from the left navigation.
3. Paste the contents of `database/migrations.sql` and click **Run**.
   - Enables `uuid-ossp` and `vector` (pgvector).
   - Creates tables (`profiles`, `documents`, `document_chunks`, `conversations`, `messages`).
   - Defines the `match_document_chunks` RPC vector cosine distance function.
   - Configures the `documents` storage bucket with folder isolation policies.
   - Enables Row Level Security (RLS) on all tables.

### 5. Google OAuth Configuration (Optional)
If you wish to enable Google One-Tap / OAuth sign-in:
1. In your Supabase Dashboard, go to **Authentication** > **Providers** > **Google**.
2. Enter your **Client ID** and **Client Secret** (from Google Cloud Console).
3. Set the Authorized Redirect URI in Google Cloud Console to:
   `https://<your-project-id>.supabase.co/auth/v1/callback`

### 6. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate `.env` with your actual service credentials:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
HOST=0.0.0.0
PORT=8000
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=800
CHUNK_OVERLAP=150
MAX_FILE_SIZE_BYTES=26214400
```

### 7. Run the Application
Start the DocuMind FastAPI server:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and navigate to:
```
http://localhost:8000
```

*(Optional for local OAuth testing)*: If your Supabase OAuth redirect is configured to port 3000, start the local OAuth forwarder in a separate terminal:
```bash
python backend/port_3000_forwarder.py
```

---

## 🔒 Security Architecture & Best Practices

- **Zero Hardcoded Identities**: Authentication strictly validates Supabase JWT signatures via `/api/auth/me`. There are no fallback identities or hardcoded demo sessions.
- **Row Level Security (RLS)**: Enforced directly at the PostgreSQL layer. Users can never query, modify, or delete another user's documents, chunks, or conversations.
- **Private Key Isolation**: All LLM and Supabase Service Role keys remain on the backend and are never sent to the browser client.
- **Git Hygiene**: `.gitignore` strictly excludes `.env`, `venv/`, local uploads, logs, and compiler caches. Run automated secret audits prior to committing.

---

## 🧪 Testing & Verification

DocuMind includes an automated testing harness in `scripts/`:

```bash
# Run isolated AI Assistant intent routing & citations test
python scripts/test_ai_assistant_routing.py

# Run full end-to-end system regression suite
python scripts/e2e_full_verification.py
```
