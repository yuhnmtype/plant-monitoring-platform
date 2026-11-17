-- Runs (M2 decisions 8-9). Drops the M1 data tables: simulated data is regenerated from the seed.
-- All data is simulated.
DROP TABLE incident_labels, context_readings, readings, sensors, profiles;

CREATE TABLE runs (
    run_id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_id       text NOT NULL,
    name             text NOT NULL,
    simulated        boolean NOT NULL CHECK (simulated),
    seed             bigint NOT NULL,
    profile_sha256   text NOT NULL,
    interval_minutes integer NOT NULL CHECK (interval_minutes > 0),
    created_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (profile_id, seed, profile_sha256)
);

-- end_ts is exclusive: a split holds the timestamps start_ts <= ts < end_ts.
CREATE TABLE run_splits (
    run_id   bigint NOT NULL REFERENCES runs (run_id) ON DELETE CASCADE,
    split    text NOT NULL,
    start_ts timestamptz NOT NULL,
    end_ts   timestamptz NOT NULL,
    PRIMARY KEY (run_id, split),
    CHECK (end_ts > start_ts)
);

CREATE TABLE sensors (
    run_id       bigint NOT NULL REFERENCES runs (run_id) ON DELETE CASCADE,
    id           text NOT NULL,
    asset        text NOT NULL,
    kind         text NOT NULL,
    unit         text NOT NULL,
    nominal_low  double precision NOT NULL,
    nominal_high double precision NOT NULL,
    PRIMARY KEY (run_id, id)
);

CREATE TABLE readings (
    run_id    bigint NOT NULL,
    sensor_id text NOT NULL,
    ts        timestamptz NOT NULL,
    value     double precision NOT NULL,
    PRIMARY KEY (run_id, sensor_id, ts),
    FOREIGN KEY (run_id, sensor_id) REFERENCES sensors (run_id, id) ON DELETE CASCADE
);

-- Optional context channel (ADR 0006): stays empty for a profile without states.
CREATE TABLE context_readings (
    run_id bigint NOT NULL REFERENCES runs (run_id) ON DELETE CASCADE,
    ts     timestamptz NOT NULL,
    state  text NOT NULL,
    PRIMARY KEY (run_id, ts)
);

-- Ground truth: read by the evaluation code only, never by detectors.
CREATE TABLE incident_labels (
    run_id        bigint NOT NULL REFERENCES runs (run_id) ON DELETE CASCADE,
    start_ts      timestamptz NOT NULL,
    end_ts        timestamptz NOT NULL,
    class_id      text NOT NULL,
    incident_type text NOT NULL CHECK (incident_type IN ('fault', 'attack')),
    split         text NOT NULL,
    PRIMARY KEY (run_id, start_ts),
    CHECK (end_ts > start_ts)
);
