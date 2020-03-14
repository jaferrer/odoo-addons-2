#!/usr/bin/env bash
HOST=$1
PORT=$2
USER=$3
DATABASE=$4
TABLE_NAME=$5
vacuumdb -h $HOST -p $PORT -U $USER -d $DATABASE --verbose --full --table $TABLE_NAME
vacuumdb -h $HOST -p $PORT -U $USER -d $DATABASE --verbose --analyze --table $TABLE_NAME
psql -h $HOST -p $PORT -U $USER -d $DATABASE -c "UPDATE odoo_monitoring_database_table SET nb_deleted_lines_since_last_vacuum_full = 0 WHERE name = '$TABLE_NAME'"
