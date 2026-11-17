-- Regular step: within one sensor and one split, consecutive timestamps differ by exactly the
-- sampling interval. Violations = rows whose gap to the previous row of the same sensor and split
-- is not the interval. Readings outside every split are ignored here (outside_splits finds them).
SELECT count(*)
FROM (
    SELECT x.ts - lag(x.ts) OVER (PARTITION BY x.sensor_id, sp.split ORDER BY x.ts) AS gap,
           r.interval_minutes
    FROM readings x
    JOIN runs r ON r.run_id = x.run_id
    JOIN run_splits sp ON sp.run_id = x.run_id AND x.ts >= sp.start_ts AND x.ts < sp.end_ts
    WHERE x.run_id = %(run_id)s
) steps
WHERE gap IS NOT NULL
  AND gap <> make_interval(mins => interval_minutes);
