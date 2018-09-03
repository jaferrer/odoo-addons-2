# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import psycopg2
import logging
from openerp import models, api, SUPERUSER_ID
from openerp.exceptions import UserError
from abc import ABCMeta, abstractmethod


logger = logging.getLogger(__name__)
ABSTRACT_MODEL_NAME = 'abstract.materialized.sql.view'


class AbstractMaterializedSqlView(models.AbstractModel):
    _name = ABSTRACT_MODEL_NAME
    _description = u"This is an helper class to manage materialized SQL view"
    _auto = False

    _sql_mat_view_name = ''
    _sql_view_name = ''
    _sql_view_definition = ''
    _replace_view = True

    def init(self, cr):

        if hasattr(super(AbstractMaterializedSqlView, self), 'init'):
            super(self, AbstractMaterializedSqlView).init(cr)

        cr.execute("""
                   CREATE or REPLACE FUNCTION DROP_VM_SQL(view_name text) RETURNS integer AS $$
                    BEGIN
                        execute format('drop view if exists %I',view_name) ;
                        return 1;
                    EXCEPTION
                        when others then return 1;
                    END;
                    $$ LANGUAGE plpgsql;
                          """)

        # prevent against Abstract class initialization
        if self._name == ABSTRACT_MODEL_NAME:
            return

        logger.info(u"Init materialized view, using Postgresql %r",
                    cr._cnx.server_version)
        self.create_or_upgrade_pg_matview_if_needs(cr, SUPERUSER_ID, context=None)

    @api.model
    def safe_properties(self):
        if not self._sql_view_definition:
            raise UserError(u"Properties must be defined in subclass",
                            u"_sql_view_definition properties should be redifined in sub class"
                            )
        if not self._sql_mat_view_name:
            self._sql_mat_view_name = self._table
        if not self._sql_view_name:
            self._sql_view_name = self._table + '_view'

    @api.model
    def create_materialized_view(self):
        params = (self._sql_mat_view_name,)
        query = """SELECT DROP_VM_SQL(%s);"""
        if self._replace_view:
            self.env.cr.execute(query, params)

        self.safe_properties()
        result = []
        logger.info("Create Materialized view %r", self._sql_mat_view_name)
        pg_version = self.env.context.get('force_pg_version', self.env.cr._cnx.server_version)
        self.change_matview_state('before_create_view', pg_version)
        try:
            pg = PGMaterializedViewManager.getInstance(pg_version)
            pg.drop_mat_view(self.env.cr, self._sql_view_name, self._sql_mat_view_name)
            self.before_create_materialized_view()
            pg.create_mat_view(self.env.cr, self._sql_view_definition, self._sql_view_name,
                               self._sql_mat_view_name)
            self.after_create_materialized_view()
        except psycopg2.Error as e:
            self.report_sql_error(e, pg_version)
        else:
            result = self.change_matview_state('after_refresh_view', pg_version)
        return result

    @api.model
    def refresh_materialized_view(self):
        self.safe_properties()
        result = self.create_or_upgrade_pg_matview_if_needs()
        if not result:
            logger.info("Refresh Materialized view %r", self._sql_mat_view_name)
            pg_version = self.env.context.get('force_pg_version', self.env.cr._cnx.server_version)
            self.change_matview_state('before_refresh_view', pg_version)
            try:
                self.before_refresh_materialized_view()
                pg = PGMaterializedViewManager.getInstance(pg_version)
                pg.refresh_mat_view(self.env.cr, self._sql_view_name, self._sql_mat_view_name)
                self.after_refresh_materialized_view()
            except psycopg2.Error as e:
                self.report_sql_error(e, pg_version)
            else:
                result = self.change_matview_state('after_refresh_view', pg_version)
        return result

    @api.model
    def create_or_upgrade_pg_matview_if_needs(self):
        self.safe_properties()
        matview_mdl = self.env['materialized.sql.view']
        ids = matview_mdl.search_materialized_sql_view_ids_from_matview_name(self._sql_mat_view_name)
        if ids:
            rec = ids.read(['pg_version', 'sql_definition', 'view_name', 'state'])
            pg_version = self.env.context.get('force_pg_version', self.env.cr._cnx.server_version)
            pg = PGMaterializedViewManager.getInstance(self.env.cr._cnx.server_version)
            if(rec[0]['pg_version'] != pg_version or
               rec[0]['sql_definition'] != self._sql_view_definition or
               rec[0]['view_name'] != self._sql_view_name or
               rec[0]['state'] in ['nonexistent', 'aborted'] or
               not pg.is_existed_relation(self.env.cr, self._sql_view_name) or
               not pg.is_existed_relation(self.env.cr, self._sql_mat_view_name)):
                self.drop_materialized_view_if_exist(rec[0]['pg_version'],
                                                     view_name=rec[0]['view_name'])
            else:
                return []

        return self.create_materialized_view()

    @api.model
    def change_matview_state(self, method_name, pg_version):
        matview_mdl = self.env['materialized.sql.view']
        values = {
            'name': self._description,
            'model_name': self._name,
            'view_name': self._sql_view_name,
            'matview_name': self._sql_mat_view_name,
            'sql_definition': self._sql_view_definition,
            'pg_version': pg_version,
        }
        matview_mdl.create_if_not_exist(values)
        method = getattr(matview_mdl.with_context({'values': values}), method_name)
        return method(self._sql_mat_view_name)

    @api.model
    def drop_materialized_view_if_exist(self, pg_version, view_name=None,
                                        mat_view_name=None):
        self.safe_properties()
        result = []
        logger.info("Drop Materialized view %r", self._sql_mat_view_name)
        try:
            self.before_drop_materialized_view()
            pg = PGMaterializedViewManager.getInstance(pg_version)
            if not view_name:
                view_name = self._sql_view_name
            if not mat_view_name:
                mat_view_name = self._sql_mat_view_name
            pg.drop_mat_view(self.env.cr, view_name, mat_view_name)
            self.after_drop_materialized_view()
        except psycopg2.Error as e:
            self.report_sql_error(e, pg_version)
        else:
            result = self.change_matview_state('after_drop_view', pg_version)
        return result

    @api.model
    def report_sql_error(self, err, pg_version):
        self.env.cr.rollback()
        self.with_context({'error_message': err.pgerror}).change_matview_state('aborted_matview', pg_version)

    @api.model
    def before_drop_materialized_view(self):
        """Method called before drop materialized view and view,
           Nothing done in abstract method, it's  hook to used in subclass
        """

    @api.model
    def after_drop_materialized_view(self):
        """Method called after drop materialized view and view,
           Nothing done in abstract method, it's  hook to used in subclass
        """

    @api.model
    def before_create_materialized_view(self):
        """Method called before create materialized view and view,
           Nothing done in abstract method, it's  hook to used in subclass
        """

    @api.model
    def after_create_materialized_view(self):
        """Method called after create materialized view and view,
           Nothing done in abstract method, it's  hook to used in subclass
        """

    @api.model
    def before_refresh_materialized_view(self):
        """Method called before refresh materialized view,
           this was made to do things like drop index before in the same transaction.

           Nothing done in abstract method, it's  hook to used in subclass
        """

    @api.model
    def after_refresh_materialized_view(self):
        """Method called after refresh materialized view,
           this was made to do things like add index after refresh data

           Nothing done in abstract method, it's  hook to used in subclass
        """

    @api.multi
    def write(self):
        raise UserError(u"Write on materialized view is forbidden",
                        u"Write on materialized view is forbidden,"
                        u"because data would be lost at the next refresh"
                        )

    @api.multi
    def create(self):
        raise UserError(u"Create data on materialized view is forbidden",
                        u"Create data on materialized view is forbidden,"
                        u"because data would be lost at the next refresh"
                        )

    @api.multi
    def unlink(self):
        raise UserError(u"Remove data on materialized view is forbidden",
                        u"Remove data on materialized view is forbidden",
                        u"because data would be lost at the next refresh"
                        )


class PGMaterializedViewManager(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def create_mat_view(self, cr, sql, view_name, mat_view_name):
        """Abstract Method to overwrite in subclass to create sql view
           and materialized sql view from sql query.
        """

    @abstractmethod
    def refresh_mat_view(self, cr, view_name, mat_view_name):
        """Abstract Method  to overwrite in subclass to refresh
           materialized sql view
        """

    @abstractmethod
    def drop_mat_view(self, cr, view_name, mat_view_name):
        """Abstract Method to overwrite in subclass to drop materialized view and clean
           every thing to its authority
        """

    def is_existed_relation(self, cr, relname):
        cr.execute("select count(*) from pg_class where relname like '%(relname)s'" %
                   {'relname': relname})
        return cr.fetchone()[0] > 0

    @classmethod
    def getInstance(cls, version):
        """Method that return the class depending pg server_version
        """
        if version >= 90300:
            return PG090300()
        else:
            return PGNoMaterializedViewSupport()


class PGNoMaterializedViewSupport(PGMaterializedViewManager):

    def create_mat_view(self, cr, sql, view_name, mat_view_name):
        cr.execute("CREATE VIEW %(view_name)s AS (%(sql)s)" %
                   dict(view_name=view_name, sql=sql, ))
        cr.execute("CREATE TABLE %(mat_view_name)s AS SELECT * FROM %(view_name)s" %
                   dict(mat_view_name=mat_view_name,
                        view_name=view_name,
                        ))

    def refresh_mat_view(self, cr, view_name, mat_view_name):
        cr.execute("DELETE FROM %(mat_view_name)s" % dict(mat_view_name=mat_view_name,
                                                          ))
        cr.execute("INSERT INTO %(mat_view_name)s SELECT * FROM %(view_name)s" %
                   dict(mat_view_name=mat_view_name,
                        view_name=view_name,
                        ))

    def drop_mat_view(self, cr, view_name, mat_view_name):
        cr.execute("DROP TABLE IF EXISTS %s CASCADE" % (mat_view_name))
        cr.execute("DROP VIEW IF EXISTS %s CASCADE" % (view_name,))


class PG090300(PGMaterializedViewManager):

    def create_mat_view(self, cr, sql, view_name, mat_view_name):
        cr.execute("CREATE VIEW %(view_name)s AS (%(sql)s)" %
                   dict(view_name=view_name, sql=sql, ))
        cr.execute("CREATE MATERIALIZED VIEW %(mat_view_name)s AS SELECT * FROM %(view_name)s" %
                   dict(mat_view_name=mat_view_name,
                        view_name=view_name,
                        ))

    def refresh_mat_view(self, cr, view_name, mat_view_name):
        cr.execute("REFRESH MATERIALIZED VIEW %(mat_view_name)s" %
                   dict(mat_view_name=mat_view_name,
                        ))

    def drop_mat_view(self, cr, view_name, mat_view_name):
        cr.execute("DROP MATERIALIZED VIEW IF EXISTS %s CASCADE" % (mat_view_name))
        cr.execute("DROP VIEW IF EXISTS %s CASCADE" % (view_name,))