CREATE TABLE IF NOT EXISTS analyst.shadow_analyst_draft_reviews (
    review_id TEXT PRIMARY KEY CHECK (review_id <> ''),
    draft_id TEXT NOT NULL REFERENCES analyst.shadow_analyst_drafts(draft_id),
    reviewer TEXT NOT NULL CHECK (reviewer <> ''),
    decision TEXT NOT NULL CHECK (decision IN ('accepted_for_publication', 'rejected', 'keep_review_required')),
    notes TEXT,
    draft_quality_score NUMERIC NOT NULL CHECK (draft_quality_score >= 0 AND draft_quality_score <= 100),
    evaluator_findings JSONB NOT NULL DEFAULT '[]',
    blocking_issues TEXT[] NOT NULL DEFAULT '{}',
    non_blocking_warnings TEXT[] NOT NULL DEFAULT '{}',
    recommendation TEXT NOT NULL CHECK (recommendation IN ('reject', 'keep_review_required', 'eligible_for_human_review')),
    accepted_payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (decision <> 'accepted_for_publication' OR cardinality(blocking_issues) = 0),
    CHECK (decision <> 'accepted_for_publication' OR accepted_payload_json ->> 'advisory_label' = 'advisory_only')
);

CREATE INDEX IF NOT EXISTS shadow_analyst_draft_reviews_draft_idx
    ON analyst.shadow_analyst_draft_reviews (draft_id);

CREATE INDEX IF NOT EXISTS shadow_analyst_draft_reviews_decision_idx
    ON analyst.shadow_analyst_draft_reviews (decision);

CREATE INDEX IF NOT EXISTS shadow_analyst_draft_reviews_created_at_idx
    ON analyst.shadow_analyst_draft_reviews (created_at DESC);
