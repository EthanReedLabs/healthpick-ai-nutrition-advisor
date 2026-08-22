BEGIN;

ALTER TABLE knowledge_chunks
    ADD COLUMN embedding vector(1024),
    ADD COLUMN embedding_model text,
    ADD COLUMN embedding_created_at timestamptz,
    ADD CONSTRAINT knowledge_chunks_embedding_complete CHECK (
        (embedding IS NULL AND embedding_model IS NULL AND embedding_created_at IS NULL)
        OR
        (embedding IS NOT NULL AND embedding_model IS NOT NULL AND embedding_created_at IS NOT NULL)
    );

CREATE INDEX knowledge_chunks_embedding_hnsw_idx
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

COMMIT;
