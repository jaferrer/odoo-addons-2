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

import datetime
import functools
import itertools
import logging
import operator
import pytz
import re
import time
from collections import defaultdict, MutableMapping
from inspect import getmembers, currentframe
from operator import itemgetter

import babel.dates
import dateutil.relativedelta
import psycopg2
from lxml import etree

import openerp
from openerp import SUPERUSER_ID
from openerp import models, api
from openerp import tools
from openerp.api import Environment
from openerp.exceptions import except_orm, AccessError, MissingError, ValidationError
from openerp.osv import fields
from openerp.osv.query import Query
from openerp.tools import frozendict, lazy_property, ormcache
from openerp.tools.config import config
from openerp.tools.func import frame_codeinfo
from openerp.tools.misc import CountingStream, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, pickle
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

regex_order = re.compile('^(\s*([a-z0-9:_]+|"[a-z0-9:_]+")(\s+(desc|asc))?\s*(,|$))+(?<!,)$', re.I)
regex_object_name = re.compile(r'^[a-z0-9_.]+$')
onchange_v7 = re.compile(r"^(\w+)\((.*)\)$")

AUTOINIT_RECALCULATE_STORED_FIELDS = 1000


def check_object_name(name):
    """ Check if the given name is a valid openerp object name.

        The _name attribute in osv and osv_memory object is subject to
        some restrictions. This function returns True or False whether
        the given name is allowed or not.

        TODO: this is an approximation. The goal in this approximation
        is to disallow uppercase characters (in some places, we quote
        table/column names and in other not, which leads to this kind
        of errors:

            psycopg2.ProgrammingError: relation "xxx" does not exist).

        The same restriction should apply to both osv and osv_memory
        objects for consistency.

    """
    if regex_object_name.match(name) is None:
        return False
    return True

def raise_on_invalid_object_name(name):
    if not check_object_name(name):
        msg = "The _name attribute %s is not valid." % name
        _logger.error(msg)
        raise except_orm('ValueError', msg)

POSTGRES_CONFDELTYPES = {
    'RESTRICT': 'r',
    'NO ACTION': 'a',
    'CASCADE': 'c',
    'SET NULL': 'n',
    'SET DEFAULT': 'd',
}

def intersect(la, lb):
    return filter(lambda x: x in lb, la)

def same_name(f, g):
    """ Test whether functions ``f`` and ``g`` are identical or have the same name """
    return f == g or getattr(f, '__name__', 0) == getattr(g, '__name__', 1)

def fix_import_export_id_paths(fieldname):
    """
    Fixes the id fields in import and exports, and splits field paths
    on '/'.

    :param str fieldname: name of the field to import/export
    :return: split field name
    :rtype: list of str
    """
    fixed_db_id = re.sub(r'([^/])\.id', r'\1/.id', fieldname)
    fixed_external_id = re.sub(r'([^/]):id', r'\1/id', fixed_db_id)
    return fixed_external_id.split('/')

def pg_varchar(size=0):
    """ Returns the VARCHAR declaration for the provided size:

    * If no size (or an empty or negative size is provided) return an
      'infinite' VARCHAR
    * Otherwise return a VARCHAR(n)

    :type int size: varchar size, optional
    :rtype: str
    """
    if size:
        if not isinstance(size, int):
            raise TypeError("VARCHAR parameter should be an int, got %s"
                            % type(size))
        if size > 0:
            return 'VARCHAR(%d)' % size
    return 'VARCHAR'

FIELDS_TO_PGTYPES = {
    fields.boolean: 'bool',
    fields.integer: 'int4',
    fields.text: 'text',
    fields.html: 'text',
    fields.date: 'date',
    fields.datetime: 'timestamp',
    fields.binary: 'bytea',
    fields.many2one: 'int4',
    fields.serialized: 'text',
}

def get_pg_type(f, type_override=None):
    """
    :param fields._column f: field to get a Postgres type for
    :param type type_override: use the provided type for dispatching instead of the field's own type
    :returns: (postgres_identification_type, postgres_type_specification)
    :rtype: (str, str)
    """
    field_type = type_override or type(f)

    if field_type in FIELDS_TO_PGTYPES:
        pg_type =  (FIELDS_TO_PGTYPES[field_type], FIELDS_TO_PGTYPES[field_type])
    elif issubclass(field_type, fields.float):
        # Explicit support for "falsy" digits (0, False) to indicate a
        # NUMERIC field with no fixed precision. The values will be saved
        # in the database with all significant digits.
        # FLOAT8 type is still the default when there is no precision because
        # it is faster for most operations (sums, etc.)
        if f.digits is not None:
            pg_type = ('numeric', 'NUMERIC')
        else:
            pg_type = ('float8', 'DOUBLE PRECISION')
    elif issubclass(field_type, (fields.char, fields.reference)):
        pg_type = ('varchar', pg_varchar(f.size))
    elif issubclass(field_type, fields.selection):
        if (f.selection and isinstance(f.selection, list) and isinstance(f.selection[0][0], int))\
                or getattr(f, 'size', None) == -1:
            pg_type = ('int4', 'INTEGER')
        else:
            pg_type = ('varchar', pg_varchar(getattr(f, 'size', None)))
    elif issubclass(field_type, fields.function):
        if f._type == 'selection':
            pg_type = ('varchar', pg_varchar())
        else:
            pg_type = get_pg_type(f, getattr(fields, f._type))
    else:
        _logger.warning('%s type not supported!', field_type)
        pg_type = None

    return pg_type

def setup(self, env):
    """ Make sure that ``self`` is set up, except for recomputation triggers. """
    if not self.setup_done:
        if self._attrs.get("compute_sql"):
            pass
        elif self.related:
            self._setup_related(env)
        else:
            self._setup_regular(env)
        self.setup_done = True

openerp.fields.Field.setup = setup


def _auto_init(self, cr, context=None):
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
    stored_fields = []              # new-style stored fields with compute
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
                if res:
                    f_pg_type = res['typname']
                    f_pg_size = res['size']
                    f_pg_notnull = res['attnotnull']
                    if isinstance(f, fields.function) and not f.store and\
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
                            ('int4', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                            ('date', 'datetime', 'TIMESTAMP', '::TIMESTAMP'),
                            ('timestamp', 'date', 'date', '::date'),
                            ('numeric', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                            ('float8', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                        ]
                        if f_pg_type == 'varchar' and f._type in ('char', 'selection') and f_pg_size and (f.size is None or f_pg_size < f.size):
                            try:
                                with cr.savepoint():
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (self._table, k, pg_varchar(f.size)), log_exceptions=False)
                            except psycopg2.NotSupportedError:
                                # In place alter table cannot be done because a view is depending of this field.
                                # Do a manual copy. This will drop the view (that will be recreated later)
                                cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO temp_change_size' % (self._table, k))
                                cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, pg_varchar(f.size)))
                                cr.execute('UPDATE "%s" SET "%s"=temp_change_size::%s' % (self._table, k, pg_varchar(f.size)))
                                cr.execute('ALTER TABLE "%s" DROP COLUMN temp_change_size CASCADE' % (self._table,))
                            cr.commit()
                            _schema.debug("Table '%s': column '%s' (type varchar) changed size from %s to %s",
                                self._table, k, f_pg_size or 'unlimited', f.size or 'unlimited')
                        for c in casts:
                            if (f_pg_type==c[0]) and (f._type==c[1]):
                                if f_pg_type != f_obj_type:
                                    ok = True
                                    cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO __temp_type_cast' % (self._table, k))
                                    cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, c[2]))
                                    cr.execute(('UPDATE "%s" SET "%s"= __temp_type_cast'+c[3]) % (self._table, k))
                                    cr.execute('ALTER TABLE "%s" DROP COLUMN  __temp_type_cast CASCADE' % (self._table,))
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
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, k))
                                cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (self._table, k, newname))
                                cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))
                                cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k), (f.string,))
                                _schema.warning("Table `%s`: column `%s` has changed type (DB=%s, def=%s), data moved to column `%s`",
                                                self._table, k, f_pg_type, f._type, newname)

                        # if the field is required and hasn't got a NOT NULL constraint
                        if f.required and f_pg_notnull == 0:
                            if has_rows:
                                self._set_default_value_on_column(cr, k, context=context)
                            # add the NOT NULL constraint
                            try:
                                cr.commit()
                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k), log_exceptions=False)
                                _schema.debug("Table '%s': column '%s': added NOT NULL constraint",
                                    self._table, k)
                            except Exception:
                                msg = "Table '%s': unable to set a NOT NULL constraint on column '%s' !\n"\
                                    "If you want to have it, you should update the records and execute manually:\n"\
                                    "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                _schema.warning(msg, self._table, k, self._table, k)
                            cr.commit()
                        elif not f.required and f_pg_notnull == 1:
                            cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, k))
                            cr.commit()
                            _schema.debug("Table '%s': column '%s': dropped NOT NULL constraint",
                                self._table, k)
                        # Verify index
                        indexname = '%s_%s_index' % (self._table, k)
                        cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = %s and tablename = %s", (indexname, self._table))
                        res2 = cr.dictfetchall()
                        if not res2 and f.select:
                            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                            cr.commit()
                            if f._type == 'text':
                                msg = "Table '%s': Adding (b-tree) index for %s column '%s'."\
                                    "This is probably useless (does not work for fulltext search) and prevents INSERTs of long texts"\
                                    " because there is a length limit for indexable btree values!\n"\
                                    "Use a search view instead if you simply want to make the field searchable."
                                _schema.warning(msg, self._table, f._type, k)
                        if res2 and not f.select:
                            cr.execute('DROP INDEX "%s_%s_index"' % (self._table, k))
                            cr.commit()
                            msg = "Table '%s': dropping index for column '%s' of type '%s' as it is not required anymore"
                            _schema.debug(msg, self._table, k, f._type)

                        if isinstance(f, fields.many2one) or (isinstance(f, fields.function) and f._type == 'many2one' and f.store):
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
                            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))
                            cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k), (f.string,))
                            _schema.debug("Table '%s': added column '%s' with definition=%s",
                                self._table, k, get_pg_type(f)[1])

                            # initialize it
                            if has_rows:
                                self._set_default_value_on_column(cr, k, context=context)

                        # remember the functions to call for the stored fields
                        if isinstance(f, fields.function):
                            order = 10
                            if f.store is not True: # i.e. if f.store is a dict
                                order = f.store[f.store.keys()[0]][2]
                            todo_end.append((order, self._update_store, (f, k)))

                        # remember new-style stored fields with compute method
                        if k in self._fields and self._fields[k].depends and not f._args.get("compute_sql"):
                            stored_fields.append(self._fields[k])

                        # and add constraints if needed
                        if isinstance(f, fields.many2one) or (isinstance(f, fields.function) and f._type == 'many2one' and f.store):
                            if f._obj not in self.pool:
                                raise except_orm('Programming Error', 'There is no reference available for %s' % (f._obj,))
                            dest_model = self.pool[f._obj]
                            ref = dest_model._table
                            # ir_actions is inherited so foreign key doesn't work on it
                            if dest_model._auto and ref != 'ir_actions' and not f._args.get("compute_sql"):
                                self._m2o_add_foreign_key_checked(k, dest_model, f.ondelete)
                        if f.select and not f._args.get("compute_sql"):
                            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                        if f.required and not f._args.get("compute_sql"):
                            try:
                                cr.commit()
                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k))
                                _schema.debug("Table '%s': column '%s': added a NOT NULL constraint",
                                    self._table, k)
                            except Exception:
                                msg = "WARNING: unable to set column %s of table %s not null !\n"\
                                    "Try to re-run: openerp-server --update=module\n"\
                                    "If it doesn't work, update records and execute manually:\n"\
                                    "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                _logger.warning(msg, k, self._table, self._table, k, exc_info=True)
                        cr.commit()

    else:
        cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
        create = not bool(cr.fetchone())

    cr.commit()     # start a new transaction

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

models.BaseModel._auto_init = _auto_init