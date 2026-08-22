BEGIN;

CREATE TABLE IF NOT EXISTS anonymous_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES anonymous_sessions(id) ON DELETE CASCADE,
    title text NOT NULL DEFAULT '新对话' CHECK (length(btrim(title)) BETWEEN 1 AND 80),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversations_session_updated_idx
    ON conversations (session_id, updated_at DESC, id);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    request_id uuid NOT NULL UNIQUE,
    user_message text NOT NULL CHECK (length(user_message) BETWEEN 1 AND 4000),
    assistant_message text NOT NULL CHECK (length(assistant_message) BETWEEN 1 AND 12000),
    route text NOT NULL CHECK (route IN ('nutrition', 'platform', 'mixed', 'out_of_scope')),
    context_eligible boolean NOT NULL DEFAULT true,
    response_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE conversation_turns
    ADD COLUMN IF NOT EXISTS response_payload jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS conversation_turns_conversation_created_idx
    ON conversation_turns (conversation_id, created_at, id);

COMMIT;
