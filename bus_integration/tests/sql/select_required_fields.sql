SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE column_name IS NOT NULL
  AND table_name like %s
  AND is_nullable = 'NO'