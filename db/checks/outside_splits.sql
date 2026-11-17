-- Nothing outside the splits: readings and context rows whose ts lies inside no split of the run
-- (start_ts <= ts < end_ts). Violations = both kinds of rows added together.
SELECT (SELECT count(*)
        FROM readings x
        WHERE x.run_id = %(run_id)s
          AND NOT EXISTS (SELECT 1
                          FROM run_splits sp
                          WHERE sp.run_id = x.run_id AND x.ts >= sp.start_ts AND x.ts < sp.end_ts))
     + (SELECT count(*)
        FROM context_readings c
        WHERE c.run_id = %(run_id)s
          AND NOT EXISTS (SELECT 1
                          FROM run_splits sp
                          WHERE sp.run_id = c.run_id AND c.ts >= sp.start_ts AND c.ts < sp.end_ts));
