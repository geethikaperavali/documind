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
