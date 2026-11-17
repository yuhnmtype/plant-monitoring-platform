-- Labels inside their split: every incident label lies inside the split it names. Violations =
-- labels whose split does not exist in run_splits, or that start before it or end after it.
SELECT count(*)
FROM incident_labels l
WHERE l.run_id = %(run_id)s
  AND NOT EXISTS (SELECT 1
                  FROM run_splits sp
                  WHERE sp.run_id = l.run_id
                    AND sp.split = l.split
                    AND l.start_ts >= sp.start_ts
                    AND l.end_ts <= sp.end_ts);
