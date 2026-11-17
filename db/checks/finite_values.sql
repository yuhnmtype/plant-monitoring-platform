-- Finite values: no NaN, +Infinity or -Infinity in readings.value. Type double precision accepts
-- all three. In PostgreSQL NaN equals NaN, so IN finds it.
SELECT count(*)
FROM readings
WHERE run_id = %(run_id)s
  AND value IN ('NaN'::double precision, 'Infinity'::double precision, '-Infinity'::double precision);
