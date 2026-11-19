# DocuMind – AI-Powered Document Intelligence Platform

DocuMind is a complete, full-stack, enterprise-grade AI document intelligence platform built with vanilla HTML5/CSS3/JavaScript on the frontend, Python FastAPI on the backend, Supabase (PostgreSQL, Auth, Storage, pgvector) for data and vector search, and Google Gemini API + Sentence Transformers for Retrieval-Augmented Generation (RAG).

---

## 🌟 Key Features

1. **Authentication System**
   - **Email & Password**: Registration, Login, Forgot Password, Reset Password with validation and show/hide password toggles.
   - **Google OAuth**: One-click "Continue with Google" sign-in via Supabase Auth with OAuth redirect and session persistence.
   - **Session Security**: Route protection, automatic redirect for unauthenticated users, session expiry handling, and secure token passing (never plaintext).

2. **Dashboard & Metrics**
   - **Live Analytics**: Dynamic database metrics for Total Documents, Storage Used, and Questions Asked.
   - **Recent Documents**: Quick overview of recent uploads with status badges, sizes, chunk counts, and timestamps.
   - **Recent Activity**: Real-time audit trail of user uploads and questions asked.

3. **Knowledge Base (Document Management)**
   - **Multi-Format Support**: Extraction and semantic chunking for **PDF** (PyMuPDF / pypdf), **Word (DOCX)** (python-docx), and **TXT** files.
   - **Drag-and-Drop Uploads**: Drag-and-drop zone with animated progress indicators and file validation (size up to 25 MB).
   - **User Data Isolation**: Every document and chunk is strictly isolated to the authenticated user via Supabase Row Level Security (RLS).
   - **Chunk Inspector**: Inspect the extracted text chunks and page numbers for any uploaded document.
   - **Safe Deletion**: Deletes original storage files, database records, and vector embeddings with user confirmation.

4. **AI Assistant – RAG (Retrieval-Augmented Generation)**
   - **Vector Similarity Search**: High-performance semantic similarity retrieval using 384-dimensional dense embeddings (`all-MiniLM-L6-v2`) and pgvector cosine distance.
   - **Strict Grounding**: Prompt engineering that instructs Gemini to base answers *strictly* on retrieved document excerpts to prevent hallucination.
   - **Grounded Source Citations**: Every answer displays the exact document name, page number, similarity score, and excerpt snippet.
   - **Conversation Threads**: Multi-turn chat with conversation history and easy creation of new threads.

5. **Clean, Minimal Visual Identity**
   - Off-white clean canvas (`#f8fafc`), muted blue accent (`#2563eb`), charcoal text (`#0f172a`), subtle borders (`#e2e8f0`).
   - Pure Vanilla JS and CSS3 without React, Next.js, or Tailwind CSS.

---

## 🏗️ Project Architecture

```
documind/
├── backend/
│   ├── main.py                  # FastAPI application entrypoint & static mounting
│   ├── config.py                # Environment configuration & settings
│   ├── auth.py                  # Supabase JWT verification & get_current_user dependency
│   ├── database.py              # Supabase admin and user client factories
│   ├── services/
│   │   ├── document_processor.py # PDF/DOCX/TXT extraction & page-aware chunking
│   │   ├── embedding_service.py # 384-dim dense embeddings (SentenceTransformers)
│   │   ├── rag_service.py       # Vector retrieval & Gemini grounded prompt pipeline
│   │   └── storage_service.py   # Supabase Storage & local fallback manager
│   └── routers/
│       ├── auth_router.py       # Auth me & config endpoints
│       ├── documents_router.py  # Document upload, list, status, delete
│       ├── chat_router.py       # RAG question answering & conversation CRUD
│       ├── dashboard_router.py  # Live stats, recent docs & activity feed
│       └── profile_router.py    # User profile & preferences
├── frontend/
│   ├── index.html               # Main Dashboard
│   ├── documents.html           # Knowledge Base
│   ├── chat.html                # AI Assistant (RAG Chat)
│   ├── settings.html            # Settings & Profile
│   ├── login.html               # Sign In
│   ├── signup.html              # Sign Up
│   ├── forgot-password.html     # Forgot Password
│   ├── reset-password.html      # Reset Password
│   ├── css/
│   │   ├── main.css             # Design system, layout, buttons, tables, badges
│   │   ├── auth.css             # Authentication cards & OAuth styling
│   │   ├── documents.css        # Dropzone, chunk modal, and controls
│   │   └── chat.css             # Chat bubbles, citations, and typing indicator
│   └── js/
│       ├── config.js            # API base URL & routes
│       ├── auth.js              # Supabase Auth client, session & route guards
│       ├── api.js               # Authenticated fetch wrapper (auto JWT Bearer)
│       ├── dashboard.js         # Dashboard controller
│       ├── documents.js         # Knowledge Base controller
│       ├── chat.js              # AI Assistant controller
│       └── settings.js          # Settings controller
├── database/
│   └── migrations.sql           # Complete Supabase PostgreSQL schema, pgvector & RLS
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation & setup instructions
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- A free [Supabase](https://supabase.com) account
- A free [Google AI Studio](https://aistudio.google.com/app/apikey) Gemini API key

### 2. Install Dependencies
```bash
cd "C:\Users\GEETHIKA P\.gemini\antigravity\scratch\documind"
pip install -r requirements.txt
```

### 3. Configure Database in Supabase
1. Create a new project in your [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to **SQL Editor** in the left sidebar.
3. Open `database/migrations.sql` from this repository, copy its contents, paste them into the SQL Editor, and click **Run**.
   - This enables `uuid-ossp` and `vector` (pgvector).
   - Creates `profiles`, `documents`, `document_chunks`, `conversations`, and `messages`.
   - Creates the `match_document_chunks` RPC vector matching function.
   - Creates the `documents` storage bucket with folder isolation policies.
   - Enables Row Level Security (RLS) on all tables.

### 4. Configure Google OAuth in Supabase (Optional for Google Sign-In)
1. In Supabase Dashboard, go to **Authentication** > **Providers** > **Google**.
2. Enable Google provider and paste your **Client ID** and **Client Secret** (from Google Cloud Console > Credentials > OAuth 2.0 Client IDs).
3. Set Authorized Redirect URI in Google Cloud Console to:
   `https://<your-project-id>.supabase.co/auth/v1/callback`

### 5. Setup Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
GEMINI_API_KEY=AIzaSy...
```

### 6. Run the Application
Start the FastAPI server:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and navigate to:
**`http://localhost:8000`**

---

## 🔒 Security & Data Isolation
- **Row Level Security (RLS)**: Enforced directly at the PostgreSQL layer. A query without a valid user JWT or from another user ID cannot return or alter any rows.
- **Storage Isolation**: Uploaded files are partitioned by user ID (`documents/<user_id>/<file_name>`).
- **No Client API Keys**: Gemini API keys and Supabase Service Role keys are **never** exposed to the browser.
- **JWT Verification**: Every protected API route verifies the Supabase access token cryptographically.
