-- Editorial contents table for storing review-passed content awaiting admin approval.
-- Tracks content through: pending -> approved -> published (or rejected).

CREATE TABLE editorial_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,           -- LangGraph thread_id for resume
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'published')),
    title TEXT NOT NULL,
    keyword TEXT NOT NULL,
    layout_json JSONB NOT NULL,        -- Full MagazineLayout JSON
    review_summary TEXT,               -- From ReviewResult.summary
    rejection_reason TEXT,             -- Required when status = 'rejected'
    admin_feedback TEXT,               -- Optional feedback on approve/revision
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,          -- Set when status -> 'published'

    CONSTRAINT rejection_reason_required
        CHECK (status != 'rejected' OR rejection_reason IS NOT NULL)
);

CREATE INDEX idx_editorial_contents_status ON editorial_contents(status);
CREATE INDEX idx_editorial_contents_thread_id ON editorial_contents(thread_id);
