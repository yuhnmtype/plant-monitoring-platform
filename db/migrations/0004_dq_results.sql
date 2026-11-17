-- Data-quality results (M2 item 5): one row per run and check, rewritten at every check run.
-- violations is the number of violating rows or pairs counted by db/checks/<check_id>.sql.
-- All data is simulated.
CREATE TABLE dq_results (
    run_id     bigint NOT NULL REFERENCES runs (run_id) ON DELETE CASCADE,
    check_id   text NOT NULL,
    passed     boolean NOT NULL,
    violations bigint NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, check_id)
);
