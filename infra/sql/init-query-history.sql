CREATE SCHEMA IF NOT EXISTS schemasense;

CREATE TABLE IF NOT EXISTS schemasense.query_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    question TEXT NOT NULL,
    sql TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    execution_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_query_history_timestamp ON schemasense.query_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_status ON schemasense.query_history(status);
