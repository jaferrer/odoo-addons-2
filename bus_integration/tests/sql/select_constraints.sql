select
    pg_constraint.conname as constraint_name,
    array_agg(pg_attribute.attname) as constraint_fields
from pg_constraint, pg_attribute, pg_class
where
	pg_class.relname like %s
	and pg_constraint.contype = 'u'
    and pg_constraint.conrelid = pg_class.oid
    and pg_attribute.attrelid = pg_class.oid
    and array[pg_attribute.attnum] <@ pg_constraint.conkey
group by pg_constraint.conname;