BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE knowledge_documents (
    id text PRIMARY KEY,
    title text NOT NULL,
    version text NOT NULL,
    source_role text NOT NULL CHECK (source_role IN ('core_nutrition', 'auxiliary_platform')),
    sha256 char(64) NOT NULL CHECK (sha256 ~ '^[A-F0-9]{64}$'),
    page_count integer NOT NULL CHECK (page_count > 0),
    manifest jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, version, sha256),
    CHECK (
        (id IN ('A', 'B') AND source_role = 'core_nutrition') OR
        (id = 'C' AND source_role = 'auxiliary_platform')
    )
);

CREATE TABLE knowledge_pages (
    id text PRIMARY KEY,
    document_id text NOT NULL REFERENCES knowledge_documents(id),
    page_number integer NOT NULL CHECK (page_number > 0),
    raw_text text NOT NULL,
    normalized_text text NOT NULL CHECK (length(normalized_text) > 0),
    blocks jsonb NOT NULL,
    quality jsonb NOT NULL,
    review_status text NOT NULL CHECK (review_status IN ('verified', 'review_required', 'rejected')),
    UNIQUE (document_id, page_number)
);

CREATE TABLE knowledge_chunks (
    id text PRIMARY KEY,
    page_id text NOT NULL REFERENCES knowledge_pages(id),
    document_id text NOT NULL REFERENCES knowledge_documents(id),
    source_role text NOT NULL CHECK (source_role IN ('core_nutrition', 'auxiliary_platform')),
    page_number integer NOT NULL CHECK (page_number > 0),
    section text NOT NULL,
    content text NOT NULL CHECK (length(content) > 0),
    allowed_routes text[] NOT NULL,
    forbidden_routes text[] NOT NULL,
    contains_table boolean NOT NULL DEFAULT false,
    unknown_glyph_count integer NOT NULL DEFAULT 0 CHECK (unknown_glyph_count >= 0),
    review_status text NOT NULL CHECK (review_status IN ('verified', 'review_required', 'rejected')),
    search_text tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    CHECK (
        (document_id IN ('A', 'B') AND source_role = 'core_nutrition' AND NOT ('platform' = ANY(allowed_routes))) OR
        (document_id = 'C' AND source_role = 'auxiliary_platform' AND allowed_routes = ARRAY['platform']::text[])
    )
);

CREATE INDEX knowledge_chunks_search_idx ON knowledge_chunks USING gin (search_text);
CREATE INDEX knowledge_chunks_source_page_idx ON knowledge_chunks (document_id, page_number);

CREATE TABLE food_facts (
    id text PRIMARY KEY,
    document_id text NOT NULL REFERENCES knowledge_documents(id) CHECK (document_id = 'A'),
    page_number integer NOT NULL CHECK (page_number BETWEEN 1 AND 5),
    section text NOT NULL,
    food_name text NOT NULL,
    category text NOT NULL,
    basis jsonb NOT NULL,
    nutrients jsonb NOT NULL,
    attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    review_status text NOT NULL CHECK (review_status IN ('verified', 'review_required', 'rejected'))
);

CREATE TABLE plan_rules (
    id text PRIMARY KEY,
    document_id text NOT NULL REFERENCES knowledge_documents(id) CHECK (document_id IN ('A', 'B')),
    page_numbers integer[] NOT NULL CHECK (cardinality(page_numbers) > 0),
    section text NOT NULL,
    rule_type text NOT NULL,
    title text NOT NULL,
    content jsonb NOT NULL,
    unknown_glyph boolean NOT NULL DEFAULT false,
    review_status text NOT NULL CHECK (review_status IN ('verified', 'review_required', 'rejected'))
);

CREATE TABLE platform_facts (
    id text PRIMARY KEY,
    document_id text NOT NULL REFERENCES knowledge_documents(id) CHECK (document_id = 'C'),
    page_numbers integer[] NOT NULL CHECK (cardinality(page_numbers) > 0),
    section text NOT NULL,
    fact_type text NOT NULL,
    title text NOT NULL,
    value jsonb NOT NULL,
    claim_scope text NOT NULL DEFAULT 'provided_whitepaper_only',
    allowed_routes text[] NOT NULL DEFAULT ARRAY['platform']::text[] CHECK (allowed_routes = ARRAY['platform']::text[]),
    forbidden_routes text[] NOT NULL DEFAULT ARRAY['nutrition', 'recommendation', 'contraindication']::text[],
    review_status text NOT NULL CHECK (review_status IN ('verified', 'review_required', 'rejected'))
);

CREATE TABLE knowledge_ingestion_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN ('running', 'passed', 'failed')),
    source_manifest_sha256 char(64),
    extractor jsonb NOT NULL,
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_summary text
);

-- Vector columns/indexes are intentionally deferred until the embedding model
-- and dimensions are frozen in the source manifest. Add them in migration 002.

COMMIT;

