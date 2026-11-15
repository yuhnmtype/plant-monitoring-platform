-- Generic tables only (ADR 0002). Everything plant-specific is rows. All data is simulated.
CREATE TABLE IF NOT EXISTS profiles (
    id        text PRIMARY KEY,
    name      text NOT NULL,
    simulated boolean NOT NULL CHECK (simulated),
    seed      bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS sensors (
    profile_id   text NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    id           text NOT NULL,
    asset        text NOT NULL,
    kind         text NOT NULL,
    unit         text NOT NULL,
    nominal_low  double precision NOT NULL,
    nominal_high double precision NOT NULL,
    PRIMARY KEY (profile_id, id)
);

CREATE TABLE IF NOT EXISTS readings (
    profile_id text NOT NULL,
    sensor_id  text NOT NULL,
    ts         timestamptz NOT NULL,
    value      double precision NOT NULL,
    PRIMARY KEY (profile_id, sensor_id, ts),
    FOREIGN KEY (profile_id, sensor_id) REFERENCES sensors (profile_id, id) ON DELETE CASCADE
);

-- Optional context channel (ADR 0006): stays empty for a profile without states.
CREATE TABLE IF NOT EXISTS context_readings (
    profile_id text NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    ts         timestamptz NOT NULL,
    state      text NOT NULL,
    PRIMARY KEY (profile_id, ts)
);

-- Ground truth: read by the evaluation code only, never by detectors.
CREATE TABLE IF NOT EXISTS incident_labels (
    profile_id    text NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    start_ts      timestamptz NOT NULL,
    end_ts        timestamptz NOT NULL,
    class_id      text NOT NULL,
    incident_type text NOT NULL CHECK (incident_type IN ('fault', 'attack')),
    split         text NOT NULL,
    PRIMARY KEY (profile_id, start_ts),
    CHECK (end_ts > start_ts)
);
