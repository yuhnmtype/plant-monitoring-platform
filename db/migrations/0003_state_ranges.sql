-- Per-state nominal range (M2 decisions 10-11). Rows exist only for a profile with states: one
-- per sensor and state, the sensor's nominal range where the profile declares none.
-- All data is simulated.
CREATE TABLE sensor_state_ranges (
    run_id    bigint NOT NULL,
    sensor_id text NOT NULL,
    state     text NOT NULL,
    low       double precision NOT NULL,
    high      double precision NOT NULL,
    PRIMARY KEY (run_id, sensor_id, state),
    FOREIGN KEY (run_id, sensor_id) REFERENCES sensors (run_id, id) ON DELETE CASCADE,
    CHECK (low < high)
);
