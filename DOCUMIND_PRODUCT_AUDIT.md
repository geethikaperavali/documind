# DOCUMIND — Comprehensive Product & Engineering Audit Report

**Audit Date:** November 22, 2026  
**Auditor Roles:** Senior Software Architect, Full-Stack Engineer, AI Systems Engineer, QA Engineer, Principal Product Auditor  
**Repository Inspected:** `C:\Users\GEETHIKA P\OneDrive\Documents\Desktop\documind`  
**Application Vision:** DocuMind is an **AI Intelligence & Decision Workspace**, built to enable enterprise analysts and knowledge workers to understand private documents, conduct authoritative external research, compare documents and statutory frameworks, verify claims, explore semantic entity relationship graphs, generate structured action deliverables, and monitor live surveillance topics over time.

---

## 1. Executive Summary

DocuMind possesses an impressive, highly ambitious architecture. Across 74 files, the codebase features 11 backend routers, 16 services, 13 frontend HTML views, and a dedicated automated test suite. It avoids framework bloat by adhering strictly to high-performance Vanilla HTML5/CSS3/JavaScript on the frontend and Python FastAPI with Supabase pgvector and Google Gemini on the backend.

However, a strict engineering trace reveals **significant discrepancies between advertised capabilities and actual production persistence/reliability**:
1. **Database Schema Cache Disconnect (Silent In-Memory Fallback):** While Section 12 of `database/migrations.sql` specifies schemas for `research_reports`, `comparison_audits`, `action_artifacts`, `watchlist_topics`, and `monitor_logs`, the remote Supabase database instance has not executed these migrations. As a result, the backend services (`action_service.py`, `research_service.py`, `monitor_service.py`) catch the PostgreSQL errors and silently store data in Python in-memory dictionaries. **On server restart or multi-worker deployment, all generated dossiers, action plans, and monitor logs are permanently lost.**
2. **Surveillance Scheduler Schema Incompatibility:** The background worker `surveillance_scheduler.py` attempts to query `.eq("status", "active")` and update `"last_checked"`, but the database migration script lacks a `status` column and names the timestamp `last_checked_at`.
3. **Truncated Document Comparison:** `compare_service.py` restricts cross-document audits to the first 15 chunks (truncated to 8,000 characters). Middle and ending sections of multi-page agreements (such as indemnities, liabilities, and termination clauses) are completely ignored.
4. **Keyword Scraper Failures in Search Grounding:** In external search grounding, queries containing natural-language lead-ins (e.g. *"Does our policy comply with..."*) caused Bing scrapers to return English grammar dictionary entries for the word "does" rather than legal or regulatory texts.
5. **Path Traversal Vulnerability:** Document uploads take `file.filename` directly without sanitizing `..` or path separators, allowing directory traversal in local storage fallbacks.
6. **Hardcoded Mobile Layout Grids:** Workspaces feature inline CSS grids (`grid-template-columns: 1fr 1fr;`) that fail to collapse on mobile screens ($375\times 812$), squishing interactive controls.

---

## 2. Overall Product Maturity Assessment

| Dimension | Score (1–10) | Maturity Level | Key Observations |
| :--- | :---: | :--- | :--- |
| **Vision & Scope Alignment** | **9.0 / 10** | Advanced | Clearly differentiates itself from generic chatbots; specialized studios cover real enterprise needs. |
| **Architecture & Modularity** | **8.5 / 10** | High | Clean separation between routers, services, orchestrators, and gateways. |
| **Database & Persistence** | **4.5 / 10** | Fragmented | Core RAG tables exist in Supabase; Decision Workspace tables fail silently to memory fallback. |
| **AI Quality & Intent Routing** | **6.5 / 10** | Moderate | Fast model failover via Gemini Gateway; query intent classification is brittle with 0 documents. |
| **Security & Privacy** | **7.5 / 10** | Robust | Hardcoded demo bypasses successfully removed; filename path traversal and CORS wildcards remain. |
| **UI/UX & Responsiveness** | **6.0 / 10** | Desktop-Biased | Elegant desktop aesthetics; broken layouts and uncollapsing grids on mobile/tablet viewports. |
| **Test Coverage & Verification** | **7.5 / 10** | Strong | E2E and routing harnesses exist, but assert on HTTP 200 rather than verified database persistence. |

**Overall Product Grade:** **C+ (Strong Architectural Prototype; Requires Hardening for Enterprise Production)**

---

## 3. Workspace-by-Workspace Evaluation

### 3.1. Workspace Dashboard (`index.html`, `dashboard.js`, `dashboard_router.py`)
- **Database Connection:** Dynamic metrics (`total_documents`, `storage_used`, `questions_asked`) correctly query `documents` and `messages` tables.
- **Recent Activity Accuracy:** Activity items combine uploads and questions chronologically. **Weakness:** Does not log Research dossiers, Action artifacts, Comparison audits, or Monitor alerts.
- **Empty & Loading States:** Handled cleanly with dedicated `.empty-state` containers and skeleton placeholders.
- **Shortcuts:** Functional navigation links to Knowledge Base, AI Assistant, and Studio workspaces.

### 3.2. Knowledge Base (`documents.html`, `documents.js`, `documents_router.py`)
- **File Uploads:** Drag-and-drop dropzone works for PDF, DOCX, and TXT files.
- **Manual Text Entry:** End-to-end operational (`#form-manual-doc` -> `POST /api/documents/text`). Chunks and embeds text into `document_chunks`.
- **Chunk Inspection:** Functional modal displays extracted text chunks, page offsets, and chunk indices.
- **Deletions:** Cascades to Supabase Storage, database records, and vector chunks.
- **Flaws Identified:**
  - **No Retry Mechanism:** Failed documents display status `failed`, but there is no retry endpoint or UI button. Users must delete and re-upload.
  - **MIME & Path Security:** Filenames are unsanitized; relies on file extension rather than magic bytes.

### 3.3. Research Studio (`research.html`, `research.js`, `research_service.py`)
- **Live Research Synthesis:** Queries Bing, OpenAlex, and Wikipedia. Enriches results using the 12-domain `SourceRegistry`.
- **Dossier Structure:** Structured executive brief, statutory framework, industry dynamics, uncertainties, and temporal flags.
- **History & Reopening:** Full UI support for filtering and opening past reports.
- **Flaws Identified:**
  - **Ephemeral Persistence:** Reports save to memory (`self._memory_reports`) due to missing table `public.research_reports`. Restarting Uvicorn wipes history.
  - **Search Stopwords:** Raw natural-language queries pollute search queries, yielding irrelevant dictionary or forum results.

### 3.4. Compare & Verify (`compare.html`, `compare.js`, `compare_service.py`)
- **Document vs Document:** Extracts semantic differences, contradictions, and omissions using Gemini JSON mode.
- **Document vs Web:** Compares document clauses against live statutory notifications.
- **Flaws Identified:**
  - **Dangerous Truncation:** Compares only the first 15 chunks (8,000 characters). Multi-page agreements lose their entire middle and back half.
  - **Arbitrary Web Queries:** In doc-vs-web, queries the search engine using literal filename string (`sample.pdf governing act...`), leading to irrelevant search hits for non-descriptive filenames.
  - **Mobile Layout Breakage:** Dropdowns sit in an inline `grid-template-columns: 1fr 1fr;` container that does not wrap on mobile viewports.

### 3.5. Knowledge Explorer (`explorer.html`, `explorer.js`, `explorer_service.py`)
- **Entity Extraction:** Identifies Statutes, Organizations, Persons, Concepts, and Dates with semantic relationship links.
- **Canvas Interactivity:** Custom HTML5 canvas with zoom, pan, node dragging, category filters, and node inspector cards.
- **Flaws Identified:**
  - **Missing Source Traceability:** Relationships and nodes display text quotes, but omit `document_id` and `page_number` references. Users cannot click to view the origin document in Knowledge Base.
  - **Scalability Limit:** Analyzes a maximum of 20 chunks limit across documents.

### 3.6. Action Studio (`action.html`, `action.js`, `action_service.py`)
- **Deliverable Generation:** Produces Implementation Plans, WBS Tasks, Compliance Checklists, and Executive Briefs.
- **Exporting:** Markdown copy to clipboard and `.md` file download work seamlessly.
- **Flaws Identified:**
  - **Ephemeral Persistence:** Persists in Python memory (`self._memory_artifacts`) because `public.action_artifacts` is absent from Supabase cache.
  - **Superficial Editing:** Users can only edit the document Title and Executive Summary. Individual task items, checkboxes, and priority tags cannot be toggled or edited in the UI.

### 3.7. Live Monitor (`monitor.html`, `monitor.js`, `monitor_service.py`, `surveillance_scheduler.py`)
- **Topic Surveillance:** Creates topics, triggers on-demand sweeps, and logs change severity (`None`, `Routine Update`, `Significant Shift`).
- **Management Controls:** Pause, Resume, and Delete UI controls are wired to `PUT /monitor/topics/{id}` and `DELETE /monitor/topics/{id}`.
- **Flaws Identified:**
  - **Scheduler Column Mismatch:** Background scheduler queries `.eq("status", "active")` and updates `last_checked`, neither of which match the `public.watchlist_topics` migration definition.
  - **No Webhook / Email Alerts:** Alerts only write to database logs; no push notification or email dispatch mechanism exists.

### 3.8. AI Assistant (`chat.html`, `chat.js`, `chat_router.py`, `orchestrator.py`)
- **Intent Routing:** Routes across Private RAG, Web Research, AI Intelligence, and Temporal Verification.
- **Grounded Citations:** Renders pills with document names, page numbers, and web URLs.
- **Multi-turn Memory:** Passes up to 6 historical conversation turns to Gemini.
- **Flaws Identified:**
  - **Zero-Document Trap:** If a new user with 0 documents asks a general query (e.g., *"What is quantum computing?"*), the orchestrator defaults to `PRIVATE_RAG`, retrieves 0 chunks, and returns: *"Based on your uploaded documents, I could not find information regarding this question."*
  - **Excessive Top-K & Low Threshold:** Threshold is set to `0.05`, passing semantically irrelevant chunks to the prompt.

### 3.9. Settings & Authentication (`settings.html`, `login.html`, `auth.js`, `auth_router.py`)
- **Authentication:** Strict Supabase Auth with Email/Password and Google OAuth.
- **Route Guards:** Private pages enforce `authManager.requireAuth()`, redirecting unauthenticated sessions to `login.html`.
- **Flaws Identified:**
  - **No In-App Password Change:** `settings.html` lacks a password update form. Authenticated users cannot change their password from within the app.

---

## 4. Functional Completeness Matrix

| Feature | Advertised Scope | Frontend Wired? | API Wired? | DB Persisted? | Real-World Functional Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **User Sign In / OAuth** | Supabase Auth Email + Google | YES | YES | YES | **COMPLETE** |
| **Route Protection** | Guard private workspaces | YES | YES | N/A | **COMPLETE** |
| **Document Upload (PDF/DOCX/TXT)** | Storage + Parsing + Embedding | YES | YES | YES | **COMPLETE** |
| **Manual Document Notes** | Ingestion of raw text | YES | YES | YES | **COMPLETE** |
| **Document Chunk Inspector** | Inspect page chunks | YES | YES | YES | **COMPLETE** |
| **Document Retry** | Re-run failed document extraction | NO | NO | NO | **MISSING** |
| **RAG Document Q&A** | Grounded question answering | YES | YES | YES | **COMPLETE** |
| **Zero-Doc General Fallback** | Fall back to general web/LLM | NO | NO | N/A | **DEFECTIVE** |
| **Universal Research Synthesis** | Multi-domain live dossiers | YES | YES | **MEMORY ONLY** | **PARTIAL (Persistence Risk)** |
| **Research History Archive** | Reopen past dossiers | YES | YES | **MEMORY ONLY** | **PARTIAL (Wiped on restart)** |
| **Doc vs Doc Comparison** | Full clause audit | YES | YES | N/A | **PARTIAL (Truncated to 15 chunks)** |
| **Doc vs Web Verification** | Statutory check against live law | YES | YES | N/A | **PARTIAL (Uses filename query)** |
| **Knowledge Graph Canvas** | Interactive entity relations | YES | YES | N/A | **COMPLETE** |
| **Graph Source Traceability** | Click node to open document/page | NO | NO | NO | **MISSING** |
| **Action Deliverable Generation** | Plans, tasks, checklists | YES | YES | **MEMORY ONLY** | **PARTIAL (Persistence Risk)** |
| **Action Item Task Toggling** | Check off items, edit priorities | NO | NO | NO | **MISSING** |
| **Action Export (Markdown)** | Clipboard and file download | YES | YES | N/A | **COMPLETE** |
| **Surveillance Topic Tracking** | Create, pause, resume, sweep | YES | YES | **MEMORY ONLY** | **PARTIAL (Persistence Risk)** |
| **Background Cron Surveillance** | Hourly/daily automated sweeps | NO | YES | NO | **BROKEN (Schema mismatch)** |
| **In-App Password Management** | Change password inside Settings | NO | NO | NO | **MISSING** |

---

## 5. Backend and API Findings

1. **Unmounted Local Storage Route:**
   - In `backend/services/storage_service.py:58`, if Supabase storage upload fails, the fallback returns `/local-files/{user_id}/{filename}`.
   - However, in `backend/main.py`, `/local-files` is **never mounted**. Attempting to access local file fallbacks returns HTTP 404.
2. **PostgreSQL Foreign Key Violations during Tests:**
   - When running test suites with mock user IDs (`00000000-0000-0000-0000-000000000001`), database inserts into `conversations` fail because `user_id` enforces a foreign key constraint referencing `auth.users(id)`.
3. **Overly Broad CORS Middleware:**
   - In `backend/config.py`, `CORS_ORIGINS` defaults to `["*"]` with `allow_credentials=True`. In browsers adhering strictly to the Fetch specification, `allow_credentials=True` combined with wildcard `*` is rejected.

---

## 6. AI Pipeline Findings

1. **Query Intent Classification Flaw (`orchestrator.py`):**
   - The method signature is `classify_intent(question, has_user_docs=True)`.
   - `orchestrate_query` calls `classify_intent(question)` without passing the user's actual document count.
   - If a user has 0 documents and asks a general question, the system defaults to Private RAG, finds 0 chunks, and returns an empty apology rather than answering.
2. **Cosine Similarity Threshold Too Low (`rag_service.py`):**
   - Threshold is hardcoded to `0.05`.
   - In `all-MiniLM-L6-v2`, random English text pairs frequently score between 0.10 and 0.20. Setting a threshold of 0.05 permits noise to dilute the LLM context. Recommended threshold: `0.35`–`0.45`.
3. **Search Stopword Pollution (`search_service.py`):**
   - Sending full conversational queries directly to Bing (e.g. *"Does our policy..."*) causes the scraper to index English grammatical definitions rather than substantive topics. The search engine needs a preliminary query-reformulation step.

---

## 7. Database and Security Findings

1. **Unapplied Migration Section 12:**
   - `database/migrations.sql` includes tables `research_reports`, `comparison_audits`, `action_artifacts`, `watchlist_topics`, and `monitor_logs`.
   - These have not been executed on the live Supabase project, causing PostgREST error `PGRST205` ("Could not find table in schema cache").
2. **Schema Inconsistency on `watchlist_topics`:**
   - Migration defines `last_checked_at` and has no `status` column.
   - Backend queries `.eq("status", "active")` and updates `last_checked`.
3. **Path Traversal Vulnerability (P0):**
   - `backend/routers/documents_router.py:62` passes `f"{doc_id}_{file.filename}"` directly to `storage_service.upload_file`.
   - In `storage_service.py:54`, `local_file_path = user_folder / file_name`.
   - If a client supplies a filename containing `../../`, the path escapes `user_folder`.
   - **Fix:** Apply `os.path.basename(file.filename)` and strip non-alphanumeric characters.
4. **Token Security: PASS:**
   - Zero hardcoded API keys, JWT secrets, or private keys found in the repository.

---

## 8. UI/UX Audit (Viewport Testing)

### Desktop ($1440 \times 900$)
- Aesthetics are clean, restrained, and professional.
- Navigation bar, topbar metrics, modal overlays, and studio cards render properly.
- Knowledge Explorer canvas scales to container dimensions.

### Tablet ($768 \times 1024$)
- Sidebar collapses into a slide-over mobile drawer with hamburger toggle.
- `.research-studio-layout` collapses cleanly into a single-column layout at 1100px.
- **Weakness:** Compare Studio dropdowns and Action Studio option cards remain tight due to uncollapsed inline grids.

### Mobile ($375 \times 812$)
- **Defect 1 (Inline Grid Overflow):** `compare.html` and `action.html` use hardcoded inline style `display: grid; grid-template-columns: 1fr 1fr;`. On a 375px screen, each column is constrained to ~170px, causing text truncation and cramped inputs.
- **Defect 2 (Inspector Drawer Dominance):** In `explorer.html`, the `.inspector-drawer` is hardcoded to `width: 320px;`. On a 375px phone, it covers nearly the entire viewport without a dark backdrop to dismiss it.
- **Defect 3 (Table Horizontal Scrolling):** Document management table lacks card-view transformation on small screens, requiring horizontal scrolling.

---

## 9. Testing Results

| Test Target | Test Method | Expected Result | Actual Result | Status | Evidence / Notes |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Auth Config** | `GET /api/auth/config` | Return public Supabase keys | Status 200, returned keys | **PASS** | Valid JSON payload |
| **Unauth Me** | `GET /api/auth/me` | Return 401 Unauthorized | Status 401 Unauthorized | **PASS** | Blocked correctly |
| **Unauth Documents**| `GET /api/documents` | Return 401 Unauthorized | Status 401 Unauthorized | **PASS** | Blocked correctly |
| **Obsolete Route** | `GET /api/auth/demo-session` | Return 404 Not Found | Status 404 Not Found | **PASS** | Route deleted |
| **Static HTML Pages**| `GET /*.html` | Return 200 for all 13 pages | All 13 returned Status 200 | **PASS** | Zero missing files |
| **AI Intent Routing**| `test_ai_assistant_routing.py`| 3 queries correctly routed | All 3 returned 200 | **PASS** | Document, live, and hybrid queries succeeded |
| **E2E Studio Suite** | `e2e_full_verification.py` | 17 studio phases complete | 17/17 phases passed HTTP 200 | **PASS** | Functional in-memory; DB save warnings logged |
| **Action DB Save** | `POST /api/action/generate` | Persist record in Supabase | In-memory fallback triggered | **FAIL** | Logged `PGRST205` (Table missing) |
| **Monitor DB Save** | `POST /api/monitor/topics` | Persist record in Supabase | In-memory fallback triggered | **FAIL** | Logged `PGRST205` (Table missing) |
| **Research DB Save**| `POST /api/research/query` | Persist record in Supabase | In-memory fallback triggered | **FAIL** | Logged `PGRST205` (Table missing) |

---

## 10. Prioritized Issue List (P0 – P3)

### P0 — Critical (Data Loss & Security Vulnerabilities)
1. **P0-1: Missing Supabase Tables for Decision Workspaces**
   - *File:* `database/migrations.sql` (Section 12)
   - *Root Cause:* Tables `research_reports`, `action_artifacts`, `watchlist_topics`, `monitor_logs`, and `comparison_audits` exist in migration script but have not been executed in the remote Supabase project.
   - *User Impact:* Severe data loss. All research reports, action deliverables, and monitoring logs are lost every time the server restarts.
   - *Fix:* Run Section 12 of `database/migrations.sql` in Supabase SQL Editor.
2. **P0-2: Unsanitized File Upload Path Traversal**
   - *File:* `backend/routers/documents_router.py:62` & `backend/services/storage_service.py:54`
   - *Root Cause:* Raw `file.filename` used in path construction.
   - *User Impact:* Arbitrary file write outside designated user folders in local storage mode.
   - *Fix:* Sanitize via `os.path.basename(file.filename)` and regex whitelist `[a-zA-Z0-9._-]`.

### P1 — High (Broken Workflows & Major Defects)
1. **P1-1: Surveillance Scheduler Schema Incompatibility**
   - *File:* `backend/services/surveillance_scheduler.py:17, 22, 53` vs `database/migrations.sql:340`
   - *Root Cause:* Code queries `status` column and `last_checked` field, which do not exist in the SQL definition (`last_checked_at`).
   - *User Impact:* Background surveillance crashes or silently fails to execute scheduled checks.
   - *Fix:* Add `status TEXT DEFAULT 'active'` to `watchlist_topics` in `migrations.sql` and standardize on `last_checked_at`.
2. **P1-2: AI Assistant Zero-Document Dead End**
   - *File:* `backend/services/orchestrator.py:22-54`
   - *Root Cause:* `classify_intent` defaults to `PRIVATE_RAG` without checking if the user has documents.
   - *User Impact:* General questions from new users return empty apologies instead of helpful web/AI answers.
   - *Fix:* Check `document_count > 0` before defaulting to `PRIVATE_RAG`; route general knowledge to `WEB_RESEARCH` or `AI_INTELLIGENCE`.
3. **P1-3: Severe Comparison Document Truncation**
   - *File:* `backend/services/compare_service.py:117-122`
   - *Root Cause:* Only takes `chunks[:15]` and slices `[:8000]` characters.
   - *User Impact:* Completely omits the middle and end of documents larger than 5 pages.
   - *Fix:* Implement map-reduce or section-based comparative chunk clustering.

### P2 — Medium (Functional Gaps & Unhandled Edge Cases)
1. **P2-1: Compare vs Web Uses Raw Filename as Search Query**
   - *File:* `backend/services/compare_service.py:170`
   - *Root Cause:* Queries `f"{doc.name} governing act current law amendments"`.
   - *User Impact:* Returns zero or useless search results if the filename is non-descriptive (`document_v2.pdf`).
   - *Fix:* Extract core legal entity or topic from document chunks before querying web.
2. **P2-2: Unmounted `/local-files` Route**
   - *File:* `backend/services/storage_service.py:58` vs `backend/main.py`
   - *Root Cause:* Storage service generates `/local-files/...` URLs, but FastAPI does not mount `/local-files`.
   - *User Impact:* HTTP 404 when clicking document preview if Supabase Storage is offline.
   - *Fix:* Mount `app.mount("/local-files", StaticFiles(directory=LOCAL_STORAGE_DIR))` in `backend/main.py`.
3. **P2-3: Action Studio Item Editing Unsupported**
   - *File:* `frontend/js/action.js:321-335`
   - *Root Cause:* Save handler only serializes title and executive summary.
   - *User Impact:* Users cannot edit tasks, toggle checklist items, or reassign priorities.
   - *Fix:* Make individual checklist items editable and persist updated JSON schema.
4. **P2-4: Missing Document Retry Endpoint**
   - *File:* `backend/routers/documents_router.py`
   - *Root Cause:* No `/api/documents/{id}/retry` route implemented.
   - *User Impact:* Failed extractions require full deletion and re-upload.
   - *Fix:* Add retry endpoint re-reading bytes from storage and re-triggering processor.

### P3 — Low (UI Polish & Usability)
1. **P3-1: Hardcoded Inline Grids on Mobile Viewports**
   - *Files:* `frontend/compare.html`, `frontend/action.html`
   - *Root Cause:* Inline styles `display: grid; grid-template-columns: 1fr 1fr;`.
   - *User Impact:* Unusable cramped inputs on 375px screens.
   - *Fix:* Move inline styles to `studios.css` with responsive breakpoint `@media (max-width: 768px) { grid-template-columns: 1fr; }`.
2. **P3-2: Graph Inspector Drawer Lacks Mobile Overlay Backdrop**
   - *File:* `frontend/css/studios.css` & `frontend/explorer.html`
   - *Root Cause:* Drawer opens over canvas at 320px width without backdrop.
   - *User Impact:* Hard to dismiss on small screens.
   - *Fix:* Add backdrop and set mobile drawer width to `100%`.
3. **P3-3: Missing In-App Password Change**
   - *File:* `frontend/settings.html`
   - *Root Cause:* Settings page has profile name and API key, but no password form.
   - *User Impact:* Users must sign out and use forgot-password flow.
   - *Fix:* Add password update form calling `supabase.auth.updateUser({ password })`.

---

## 11. Recommended Implementation Order

```
Phase 1: Database Integrity (P0)
  ├── 1. Execute Section 12 in Supabase SQL Editor (Fixes data loss across all studios)
  └── 2. Patch database/migrations.sql schema to include status column on watchlist_topics

Phase 2: Security & Backend Hardening (P0, P1, P2)
  ├── 3. Sanitize file upload names with os.path.basename (Eliminates path traversal)
  ├── 4. Mount /local-files static directory in backend/main.py (Fixes offline file previews)
  └── 5. Synchronize surveillance_scheduler.py column names (last_checked_at, status)

Phase 3: AI Pipeline & Intelligence Tuning (P1, P2)
  ├── 6. Fix orchestrator.py zero-document intent classification (Eliminates dead ends)
  ├── 7. Raise RAG cosine similarity threshold from 0.05 to 0.35 (Removes hallucinated noise)
  ├── 8. Upgrade compare_service.py to extract semantic topics rather than querying raw filenames
  └── 9. Expand compare_service.py chunk coverage beyond the first 15 chunks

Phase 4: UI/UX & Responsive Refinement (P2, P3)
  ├── 10. Extract inline 1fr 1fr grids to studios.css with mobile 1fr collapse
  ├── 11. Make Action Studio checklist and task items individually editable/toggleable
  ├── 12. Add in-app password update section in settings.html
  └── 13. Add retry endpoint in documents_router.py
```

---

## 12. Dependencies Between Fixes

- **Fix 1 (`migrations.sql` Section 12 execution) is a prerequisite for Fixes 5, 8, and 11.** Without the physical database tables created in Supabase, backend fixes to `action_service`, `research_service`, and `monitor_service` will continue falling back to memory.
- **Fix 3 (Filename sanitization) must be deployed before Fix 4 (`/local-files` mounting)** to prevent directory traversal over exposed static routes.
- **Fix 6 (Orchestrator zero-document detection) depends on database query to count user documents.**

---

## 13. Features That Are Working Well (DO NOT BREAK)

1. **Branded Initial Application Loader:**
   - Fast, clean, professional splash experience.
   - Initializes Supabase session, avoids UI flicker, and handles unauthenticated state gracefully.
2. **Supabase JWT Authentication & Route Guards:**
   - `authManager.requireAuth()` operates securely on private pages.
   - Obsolete `/auth/demo-session` hardcoded identity has been cleanly eradicated.
   - Token-free requests correctly return HTTP 401 Unauthorized.
3. **Core Document Ingestion & Chunking:**
   - PyMuPDF extraction, sentence chunking, and SentenceTransformer dense vector embedding generation function reliably.
   - Manual text note ingestion is fully operational.
4. **Interactive Knowledge Explorer Canvas:**
   - Smooth physics-based HTML5 canvas with zoom, pan, dragging, and category filtering.
5. **Universal Source Registry:**
   - Robust categorization of official authorities across 12 professional domains with credibility badges.
6. **Gemini Gateway Multi-Model Failover:**
   - Automatically falls back across `gemini-3.1-flash-lite`, `gemini-2.5-flash`, and `gemini-2.0-flash`.
7. **Action Studio Markdown Export:**
   - High-quality copy-to-clipboard and `.md` file download.

---

## 14. Realistic Assessment: Path to Enterprise Production

DocuMind is an exceptionally well-conceived application. Its core distinction—providing a unified workspace for deep research, statutory verification, and actionable deliverables—is far superior to typical chat interfaces.

However, **it cannot currently be considered production-ready due to silent database persistence fallbacks (P0) and mobile layout constraints (P3)**. A developer deploying this project today would observe passing tests and functional screens, yet users would find all their dossiers, action plans, and monitor feeds wiped upon the first server restart.

By following the 4-phase implementation plan outlined above—starting with running Section 12 of `database/migrations.sql` in Supabase and sanitizing file upload paths—DocuMind will transform from an impressive prototype into a rock-solid, enterprise-grade AI Decision Workspace.
