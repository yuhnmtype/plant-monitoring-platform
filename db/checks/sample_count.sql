-- Sample count: for each (sensor, split) the stored readings in [start_ts, end_ts) must number
-- (end_ts - start_ts) / interval. Violations = (sensor, split) pairs that differ. Only readings
-- inside a split are counted, so the gaps between splits are expected holes.
SELECT count(*)
FROM runs r
JOIN run_splits sp ON sp.run_id = r.run_id
JOIN sensors s ON s.run_id = r.run_id
WHERE r.run_id = %(run_id)s
  AND EXTRACT(EPOCH FROM sp.end_ts - sp.start_ts) / 60.0 / r.interval_minutes
      <> (SELECT count(*)
          FROM readings x
          WHERE x.run_id = r.run_id
            AND x.sensor_id = s.id
            AND x.ts >= sp.start_ts
            AND x.ts < sp.end_ts);
