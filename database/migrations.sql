-- ==============================================================================
-- DOCUMIND DATABASE MIGRATION SCRIPT
-- Supabase PostgreSQL + pgvector + Row Level Security (RLS)
-- ==============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Profiles Table (Synchronized with auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    preferences JSONB DEFAULT '{"theme": "light", "notifications": true}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- Trigger to handle new user registration automatically
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', SPLIT_PART(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'avatar_url', '')
    )
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email,
        full_name = CASE WHEN profiles.full_name = '' THEN EXCLUDED.full_name ELSE profiles.full_name END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 3. Documents Table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'pdf', 'docx', 'txt'
    file_size BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'processing', -- 'processing', 'ready', 'failed'
    error_message TEXT,
    chunk_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 4. Document Chunks Table (with Vector Embeddings)
-- Dimension 384 for sentence-transformers/all-MiniLM-L6-v2
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INT DEFAULT 1,
    chunk_index INT NOT NULL DEFAULT 0,
    embedding VECTOR(384),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 5. Conversations Table
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 6. Messages Table
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 7. Indexes for performance and vector similarity search
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON public.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_id ON public.document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON public.messages(user_id);

-- HNSW vector index for high performance cosine distance similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw 
ON public.document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- 8. Vector Matching RPC Function for RAG Retrieval
CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding VECTOR(384),
    match_threshold FLOAT DEFAULT 0.0,
    match_count INT DEFAULT 5,
    filter_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    document_name TEXT,
    content TEXT,
    page_number INT,
    chunk_index INT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        d.name AS document_name,
        dc.content,
        dc.page_number,
        dc.chunk_index,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks dc
    JOIN public.documents d ON d.id = dc.document_id
    WHERE (filter_user_id IS NULL OR dc.user_id = filter_user_id)
      AND (1 - (dc.embedding <=> query_embedding)) >= match_threshold
    ORDER BY dc.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- 9. Row Level Security (RLS) Setup
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Profiles Policies
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert their own profile" ON public.profiles;
CREATE POLICY "Users can insert their own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Documents Policies
DROP POLICY IF EXISTS "Users can select own documents" ON public.documents;
CREATE POLICY "Users can select own documents"
    ON public.documents FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own documents" ON public.documents;
CREATE POLICY "Users can insert own documents"
    ON public.documents FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
CREATE POLICY "Users can update own documents"
    ON public.documents FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;
CREATE POLICY "Users can delete own documents"
    ON public.documents FOR DELETE
    USING (auth.uid() = user_id);

-- Document Chunks Policies
DROP POLICY IF EXISTS "Users can select own document chunks" ON public.document_chunks;
CREATE POLICY "Users can select own document chunks"
    ON public.document_chunks FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own document chunks" ON public.document_chunks;
CREATE POLICY "Users can insert own document chunks"
    ON public.document_chunks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own document chunks" ON public.document_chunks;
CREATE POLICY "Users can update own document chunks"
    ON public.document_chunks FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own document chunks" ON public.document_chunks;
CREATE POLICY "Users can delete own document chunks"
    ON public.document_chunks FOR DELETE
    USING (auth.uid() = user_id);

-- Conversations Policies
DROP POLICY IF EXISTS "Users can select own conversations" ON public.conversations;
CREATE POLICY "Users can select own conversations"
    ON public.conversations FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own conversations" ON public.conversations;
CREATE POLICY "Users can insert own conversations"
    ON public.conversations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own conversations" ON public.conversations;
CREATE POLICY "Users can update own conversations"
    ON public.conversations FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own conversations" ON public.conversations;
CREATE POLICY "Users can delete own conversations"
    ON public.conversations FOR DELETE
    USING (auth.uid() = user_id);

-- Messages Policies
DROP POLICY IF EXISTS "Users can select own messages" ON public.messages;
CREATE POLICY "Users can select own messages"
    ON public.messages FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own messages" ON public.messages;
CREATE POLICY "Users can insert own messages"
    ON public.messages FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own messages" ON public.messages;
CREATE POLICY "Users can delete own messages"
    ON public.messages FOR DELETE
    USING (auth.uid() = user_id);

-- 10. Supabase Storage Setup Instructions (Executed in Storage SQL / UI)
-- Insert 'documents' bucket if not exists
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents', 
    'documents', 
    false, 
    52428800, -- 50MB limit
    ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
)
ON CONFLICT (id) DO UPDATE
SET public = false,
    file_size_limit = 52428800,
    allowed_mime_types = ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];

-- Storage RLS Policies: Isolates files inside a folder named after the user's UUID
DROP POLICY IF EXISTS "Allow user to upload to own folder" ON storage.objects;
CREATE POLICY "Allow user to upload to own folder"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

DROP POLICY IF EXISTS "Allow user to read own files" ON storage.objects;
CREATE POLICY "Allow user to read own files"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

DROP POLICY IF EXISTS "Allow user to update own files" ON storage.objects;
CREATE POLICY "Allow user to update own files"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

DROP POLICY IF EXISTS "Allow user to delete own files" ON storage.objects;
CREATE POLICY "Allow user to delete own files"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

-- 11. Grant schema privileges to API roles (anon, authenticated, service_role)
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO anon, authenticated, service_role;

-- ==============================================================================
-- 12. DOCUMIND DECISION WORKSPACE TABLES (Intelligence & Studios)
-- ==============================================================================

-- 12.1 Research Reports (Research Studio)
CREATE TABLE IF NOT EXISTS public.research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    depth TEXT NOT NULL DEFAULT 'comprehensive',
    report_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 12.2 Comparison Audits (Compare & Verify)
CREATE TABLE IF NOT EXISTS public.comparison_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    audit_type TEXT NOT NULL DEFAULT 'doc_vs_doc', -- 'doc_vs_doc' or 'doc_vs_web'
    title TEXT NOT NULL,
    doc_a_id UUID REFERENCES public.documents(id) ON DELETE SET NULL,
    doc_b_id UUID REFERENCES public.documents(id) ON DELETE SET NULL,
    audit_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 12.3 Action Artifacts (Action Studio)
CREATE TABLE IF NOT EXISTS public.action_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL, -- 'plan', 'tasks', 'checklist', 'business_analysis', 'report', 'study'
    title TEXT NOT NULL,
    source_title TEXT,
    artifact_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 12.4 Watchlist Topics (Live Monitor)
CREATE TABLE IF NOT EXISTS public.watchlist_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    frequency TEXT DEFAULT 'daily',
    status TEXT DEFAULT 'active',
    last_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 12.5 Monitor Logs (Live Monitor Sweeps)
CREATE TABLE IF NOT EXISTS public.monitor_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    change_level TEXT NOT NULL, -- 'None', 'Routine Update', 'Significant Shift'
    headline TEXT NOT NULL,
    log_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- Indexes for decision workspace tables
CREATE INDEX IF NOT EXISTS idx_research_reports_user_id ON public.research_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_research_reports_created ON public.research_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comparison_audits_user_id ON public.comparison_audits(user_id);
CREATE INDEX IF NOT EXISTS idx_action_artifacts_user_id ON public.action_artifacts(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_topics_user_id ON public.watchlist_topics(user_id);
CREATE INDEX IF NOT EXISTS idx_monitor_logs_user_id ON public.monitor_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_monitor_logs_created ON public.monitor_logs(created_at DESC);

-- Enable RLS on all new tables
ALTER TABLE public.research_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comparison_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monitor_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for research_reports
DROP POLICY IF EXISTS "Users can manage own research reports" ON public.research_reports;
CREATE POLICY "Users can manage own research reports"
    ON public.research_reports FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policies for comparison_audits
DROP POLICY IF EXISTS "Users can manage own comparison audits" ON public.comparison_audits;
CREATE POLICY "Users can manage own comparison audits"
    ON public.comparison_audits FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policies for action_artifacts
DROP POLICY IF EXISTS "Users can manage own action artifacts" ON public.action_artifacts;
CREATE POLICY "Users can manage own action artifacts"
    ON public.action_artifacts FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policies for watchlist_topics
DROP POLICY IF EXISTS "Users can manage own watchlist topics" ON public.watchlist_topics;
CREATE POLICY "Users can manage own watchlist topics"
    ON public.watchlist_topics FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policies for monitor_logs
DROP POLICY IF EXISTS "Users can manage own monitor logs" ON public.monitor_logs;
CREATE POLICY "Users can manage own monitor logs"
    ON public.monitor_logs FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Re-grant schema privileges to all roles
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
