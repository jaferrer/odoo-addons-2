# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging

import psycopg2
import itertools

import openerp
from openerp import SUPERUSER_ID
from openerp import api
from openerp.exceptions import except_orm, MissingError
from openerp.osv import fields
from openerp.models import raise_on_invalid_object_name, pg_varchar, get_pg_type


_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class BaseModelExtend(openerp.models.BaseModel):
    _name = 'basemodelcustom.extend'
    _auto = False

    def __init__(self, pool, cr):

        @api.cr_context
        def _auto_init_custom(self, cr, context=None):
            """

            Call _field_create and, unless _auto is False:

            - create the corresponding table in database for the model,
            - possibly add the parent columns in database,
            - possibly add the columns 'create_uid', 'create_date', 'write_uid',
              'write_date' in database if _log_access is True (the default),
            - report on database columns no more existing in _columns,
            - remove no more existing not null constraints,
            - alter existing database columns to match _columns,
            - create database tables to match _columns,
            - add database indices to match _columns,
            - save in self._foreign_keys a list a foreign keys to create (see
              _auto_end).

            """
            self._foreign_keys = set()
            raise_on_invalid_object_name(self._name)

            # This prevents anything called by this method (in particular default
            # values) from prefetching a field for which the corresponding column
            # has not been added in database yet!
            context = dict(context or {}, prefetch_fields=False)

            # Make sure an environment is available for get_pg_type(). This is
            # because we access column.digits, which retrieves a cursor from
            # existing environments.
            env = api.Environment(cr, SUPERUSER_ID, context)

            store_compute = False
            stored_fields = []  # new-style stored fields with compute
            todo_end = []
            update_custom_fields = context.get('update_custom_fields', False)
            self._field_create(cr, context=context)
            create = not self._table_exist(cr)
            if self._auto:

                if create:
                    self._create_table(cr)
                    has_rows = False
                else:
                    cr.execute('SELECT 1 FROM "%s" LIMIT 1' % self._table)
                    has_rows = cr.rowcount

                cr.commit()
                if self._parent_store:
                    if not self._parent_columns_exist(cr):
                        self._create_parent_columns(cr)
                        store_compute = True

                self._check_removed_columns(cr, log=False)

                # iterate on the "object columns"
                column_data = self._select_column_data(cr)

                for k, f in self._columns.iteritems():
                    drop = """drop function if exists "%s"(%s)""" % (k, self._table)
                    cr.execute(drop)
                    if k == 'id':
                        continue
                    # Don't update custom (also called manual) fields
                    if f.manual and not update_custom_fields:
                        continue

                    if isinstance(f, fields.one2many):
                        self._o2m_raise_on_missing_reference(cr, f)

                    elif isinstance(f, fields.many2many):
                        res = self._m2m_raise_or_create_relation(cr, f)
                        if res and self._fields[k].depends:
                            stored_fields.append(self._fields[k])

                    else:
                        res = column_data.get(k)

                        # The field is not found as-is in database, try if it
                        # exists with an old name.
                        if not res and hasattr(f, 'oldname'):
                            res = column_data.get(f.oldname)
                            if res:
                                cr.execute('ALTER TABLE "%s" RENAME "%s" TO "%s"' % (self._table, f.oldname, k))
                                res['attname'] = k
                                column_data[k] = res
                                _schema.debug("Table '%s': renamed column '%s' to '%s'",
                                              self._table, f.oldname, k)

                        # The field already exists in database. Possibly
                        # change its type, rename it, drop it or change its
                        # constraints.
                        if f._args.get("compute_sql"):
                            cr.execute('ALTER TABLE "%s" DROP COLUMN IF EXISTS "%s" CASCADE' % (self._table, k))
                            res = False
                        if res:
                            f_pg_type = res['typname']
                            f_pg_size = res['size']
                            f_pg_notnull = res['attnotnull']
                            if isinstance(f, fields.function) and not f.store and \
                                    not getattr(f, 'nodrop', False):
                                _logger.info('column %s (%s) converted to a function, removed from table %s',
                                             k, f.string, self._table)
                                cr.execute('ALTER TABLE "%s" DROP COLUMN "%s" CASCADE' % (self._table, k))
                                cr.commit()
                                _schema.debug("Table '%s': dropped column '%s' with cascade",
                                              self._table, k)
                                f_obj_type = None
                            else:
                                f_obj_type = get_pg_type(f) and get_pg_type(f)[0]

                            if f_obj_type:
                                ok = False
                                casts = [
                                    ('text', 'char', pg_varchar(f.size), '::%s' % pg_varchar(f.size)),
                                    ('varchar', 'text', 'TEXT', ''),
                                    ('int4', 'float', get_pg_type(f)[1], '::' + get_pg_type(f)[1]),
                                    ('date', 'datetime', 'TIMESTAMP', '::TIMESTAMP'),
                                    ('timestamp', 'date', 'date', '::date'),
                                    ('numeric', 'float', get_pg_type(f)[1], '::' + get_pg_type(f)[1]),
                                    ('float8', 'float', get_pg_type(f)[1], '::' + get_pg_type(f)[1]),
                                ]
                                if f_pg_type == 'varchar' and f._type in ('char', 'selection') and f_pg_size and (
                                                f.size is None or f_pg_size < f.size):
                                    try:
                                        with cr.savepoint():
                                            cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (
                                                self._table, k, pg_varchar(f.size)), log_exceptions=False)
                                    except psycopg2.NotSupportedError:
                                        # In place alter table cannot be done because a view is depending of this field.
                                        # Do a manual copy. This will drop the view (that will be recreated later)
                                        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO temp_change_size' % (
                                            self._table, k))
                                        cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (
                                            self._table, k, pg_varchar(f.size)))
                                        cr.execute('UPDATE "%s" SET "%s"=temp_change_size::%s' % (
                                            self._table, k, pg_varchar(f.size)))
                                        cr.execute('ALTER TABLE "%s" DROP COLUMN temp_change_size CASCADE' % (
                                            self._table,))
                                    cr.commit()
                                    _schema.debug(
                                        "Table '%s': column '%s' (type varchar) changed size from %s to %s",
                                        self._table, k, f_pg_size or 'unlimited', f.size or 'unlimited')
                                for c in casts:
                                    if (f_pg_type == c[0]) and (f._type == c[1]):
                                        if f_pg_type != f_obj_type:
                                            ok = True
                                            cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO __temp_type_cast' % (
                                                self._table, k))
                                            cr.execute(
                                                'ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, c[2]))
                                            cr.execute(('UPDATE "%s" SET "%s"= __temp_type_cast' + c[3]) % (
                                                self._table, k))
                                            cr.execute('ALTER TABLE "%s" DROP COLUMN  __temp_type_cast CASCADE' % (
                                                self._table,))
                                            cr.commit()
                                            _schema.debug("Table '%s': column '%s' changed type from %s to %s",
                                                          self._table, k, c[0], c[1])
                                        break

                                if f_pg_type != f_obj_type:
                                    if not ok:
                                        i = 0
                                        while True:
                                            newname = k + '_moved' + str(i)
                                            cr.execute("SELECT count(1) FROM pg_class c,pg_attribute a " \
                                                       "WHERE c.relname=%s " \
                                                       "AND a.attname=%s " \
                                                       "AND c.oid=a.attrelid ", (self._table, newname))
                                            if not cr.fetchone()[0]:
                                                break
                                            i += 1
                                        if f_pg_notnull:
                                            cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (
                                                self._table, k))
                                        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (
                                            self._table, k, newname))
                                        cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (
                                            self._table, k, get_pg_type(f)[1]))
                                        cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k),
                                                   (f.string,))
                                        _schema.warning(
                                            "Table `%s`: column `%s` has changed type (DB=%s, def=%s), data moved to column `%s`",
                                            self._table, k, f_pg_type, f._type, newname)

                                # if the field is required and hasn't got a NOT NULL constraint
                                if f.required and f_pg_notnull == 0:
                                    if has_rows:
                                        self._set_default_value_on_column(cr, k, context=context)
                                    # add the NOT NULL constraint
                                    try:
                                        cr.commit()
                                        cr.execute(
                                            'ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k),
                                            log_exceptions=False)
                                        _schema.debug("Table '%s': column '%s': added NOT NULL constraint",
                                                      self._table, k)
                                    except Exception:
                                        msg = "Table '%s': unable to set a NOT NULL constraint on column '%s' !\n" \
                                              "If you want to have it, you should update the records and execute manually:\n" \
                                              "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                        _schema.warning(msg, self._table, k, self._table, k)
                                    cr.commit()
                                elif not f.required and f_pg_notnull == 1:
                                    cr.execute(
                                        'ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, k))
                                    cr.commit()
                                    _schema.debug("Table '%s': column '%s': dropped NOT NULL constraint",
                                                  self._table, k)
                                # Verify index
                                indexname = '%s_%s_index' % (self._table, k)
                                cr.execute(
                                    "SELECT indexname FROM pg_indexes WHERE indexname = %s and tablename = %s",
                                    (indexname, self._table))
                                res2 = cr.dictfetchall()
                                if not res2 and f.select:
                                    cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (
                                        self._table, k, self._table, k))
                                    cr.commit()
                                    if f._type == 'text':
                                        msg = "Table '%s': Adding (b-tree) index for %s column '%s'." \
                                              "This is probably useless (does not work for fulltext search) and prevents INSERTs of long texts" \
                                              " because there is a length limit for indexable btree values!\n" \
                                              "Use a search view instead if you simply want to make the field searchable."
                                        _schema.warning(msg, self._table, f._type, k)
                                if res2 and not f.select:
                                    cr.execute('DROP INDEX "%s_%s_index"' % (self._table, k))
                                    cr.commit()
                                    msg = "Table '%s': dropping index for column '%s' of type '%s' as it is not required anymore"
                                    _schema.debug(msg, self._table, k, f._type)

                                if isinstance(f, fields.many2one) or (
                                                isinstance(f, fields.function) and f._type == 'many2one' and f.store):
                                    dest_model = self.pool[f._obj]
                                    if dest_model._auto and dest_model._table != 'ir_actions':
                                        self._m2o_fix_foreign_key(cr, self._table, k, dest_model, f.ondelete)

                        # The field doesn't exist in database. Create it if necessary.
                        else:
                            if not isinstance(f, fields.function) or f.store:
                                if f._args.get("compute_sql"):
                                    drop = """drop function if exists %s(%s)""" % (k, self._table)
                                    cr.execute(drop)
                                    query = """
                                        CREATE FUNCTION %s(%s)
                                          RETURNS %s AS
                                        $func$
                                            %s
                                        $func$ LANGUAGE SQL STABLE
                                                                        """ % (
                                        k, self._table, get_pg_type(f)[1], f._args.get("compute_sql"))
                                    cr.execute(query.replace("return_type", get_pg_type(f)[1]))
                                else:
                                    # add the missing field
                                    cr.execute(
                                        'ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))
                                    cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k), (f.string,))
                                    _schema.debug("Table '%s': added column '%s' with definition=%s",
                                                  self._table, k, get_pg_type(f)[1])

                                    # initialize it
                                    if has_rows:
                                        self._set_default_value_on_column(cr, k, context=context)

                                # remember the functions to call for the stored fields
                                if isinstance(f, fields.function):
                                    order = 10
                                    if f.store is not True:  # i.e. if f.store is a dict
                                        order = f.store[f.store.keys()[0]][2]
                                    todo_end.append((order, self._update_store, (f, k)))

                                # remember new-style stored fields with compute method
                                if k in self._fields and self._fields[k].depends and not f._args.get("compute_sql"):
                                    stored_fields.append(self._fields[k])

                                # and add constraints if needed
                                if isinstance(f, fields.many2one) or (
                                                isinstance(f, fields.function) and f._type == 'many2one' and f.store):
                                    if f._obj not in self.pool:
                                        raise except_orm('Programming Error',
                                                         'There is no reference available for %s' % (f._obj,))
                                    dest_model = self.pool[f._obj]
                                    ref = dest_model._table
                                    # ir_actions is inherited so foreign key doesn't work on it
                                    if dest_model._auto and ref != 'ir_actions' and not f._args.get("compute_sql"):
                                        self._m2o_add_foreign_key_checked(k, dest_model, f.ondelete)
                                if f.select and not f._args.get("compute_sql"):
                                    cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (
                                        self._table, k, self._table, k))
                                if f.required and not f._args.get("compute_sql"):
                                    try:
                                        cr.commit()
                                        cr.execute(
                                            'ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k))
                                        _schema.debug("Table '%s': column '%s': added a NOT NULL constraint",
                                                      self._table, k)
                                    except Exception:
                                        msg = "WARNING: unable to set column %s of table %s not null !\n" \
                                              "Try to re-run: openerp-server --update=module\n" \
                                              "If it doesn't work, update records and execute manually:\n" \
                                              "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                        _logger.warning(msg, k, self._table, self._table, k, exc_info=True)
                                cr.commit()

            else:
                cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
                create = not bool(cr.fetchone())

            cr.commit()  # start a new transaction

            if self._auto:
                self._add_sql_constraints(cr)

            if create:
                self._execute_sql(cr)

            if store_compute:
                self._parent_store_compute(cr)
                cr.commit()

            if stored_fields:
                # trigger computation of new-style stored fields with a compute
                def func(cr):
                    _logger.info("Storing computed values of %s fields %s",
                                 self._name, ', '.join(sorted(f.name for f in stored_fields)))
                    recs = self.browse(cr, SUPERUSER_ID, [], {'active_test': False})
                    recs = recs.search([])
                    if recs:
                        map(recs._recompute_todo, stored_fields)
                        recs.recompute()

                todo_end.append((1000, func, ()))

            return todo_end

        @api.model
        def recompute_custom(self):
            """ Recompute stored function fields. The fields and records to
                recompute have been determined by method :meth:`modified`.
            """
            while self.env.has_todo():
                field, recs = self.env.get_todo()
                # evaluate the fields to recompute, and save them to database
                names = [
                    f.name
                    for f in field.computed_fields
                    if f.store and self.env.field_todo(f) and (not f._attrs or not f._attrs.get("compute_sql"))
                ]
                for rec in recs:
                    try:
                        values = rec._convert_to_write({
                            name: rec[name] for name in names
                        })
                        with rec.env.norecompute():
                            map(rec._recompute_done, field.computed_fields)
                            rec._write(values)
                    except MissingError:
                        pass
                # mark the computed fields as done
                map(recs._recompute_done, field.computed_fields)

        @api.cr_uid_context
        def _create_custom(self, cr, user, vals, context=None):
            old_vals = {}
            for key, val in vals.iteritems():
                field = self._fields.get(key)
                if field and (not field._attrs or not field._attrs.get('compute_sql')):
                    if field.column or field.inherited:
                        old_vals[key] = val

            id_new = _create_original(self, cr, user, old_vals, context)
            return id_new

        if not hasattr(openerp.models.BaseModel, "monkey_done"):
            _create_original = openerp.models.BaseModel._create
            openerp.models.BaseModel.monkey_done = True
            openerp.models.BaseModel._auto_init = _auto_init_custom
            openerp.models.BaseModel.recompute = recompute_custom
            openerp.models.BaseModel._create = _create_custom
        super(BaseModelExtend, self).__init__(pool, cr)
