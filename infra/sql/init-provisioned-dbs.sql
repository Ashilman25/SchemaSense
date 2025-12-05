--dbs im managing 

CREATE TABLE IF NOT EXISTS provisioned_dbs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    db_name VARCHAR(255) NOT NULL UNIQUE,
    db_role VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mode VARCHAR(50) NOT NULL CHECK (mode IN ('managed', 'ephemeral')),
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_provisioned_dbs_session_id ON provisioned_dbs(session_id);
CREATE INDEX IF NOT EXISTS idx_provisioned_dbs_status ON provisioned_dbs(status);
CREATE INDEX IF NOT EXISTS idx_provisioned_dbs_last_used ON provisioned_dbs(last_used_at);
