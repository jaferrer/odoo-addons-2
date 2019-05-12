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

import openerp
from openerp import SUPERUSER_ID, api
from openerp.osv import expression

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class BaseModelExtend(openerp.models.BaseModel):
    _name = 'basemodelcustom.extend'
    _auto = False

    def __init__(self, pool, cr):

        @api.cr_uid
        def _search_custom(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False,
                    access_rights_uid=None):
            """
            Private implementation of search() method, allowing specifying the uid to use for the access right check.
            This is useful for example when filling in the selection list for a drop-down and avoiding access rights errors,
            by specifying ``access_rights_uid=1`` to bypass access rights check, but not ir.rules!
            This is ok at the security level because this method is private and not callable through XML-RPC.

            :param access_rights_uid: optional user ID to use when checking access rights
                                      (not for ir.rules, this is only for ir.model.access)
            """
            if context is None:
                context = {}
            self.check_access_rights(cr, access_rights_uid or user, 'read')

            # For transient models, restrict access to the current user, except for the super-user
            if self.is_transient() and self._log_access and user != SUPERUSER_ID:
                args = expression.AND(([('create_uid', '=', user)], args or []))

            query = self._where_calc(cr, user, args, context=context)
            self._apply_ir_rules(cr, user, query, 'read', context=context)
            order_by = self._generate_order_by(order, query)
            from_clause, where_clause, where_clause_params = query.get_sql()

            where_str = where_clause and (" WHERE %s" % where_clause) or ''

            if count:
                if context.get("load_count_stat"):
                    self.refresh_stat(cr, from_clause.replace("\"", ""))
                    query_str = 'SELECT id FROM ' + from_clause + where_str
                    query_eval = cr.mogrify(query_str, where_clause_params)
                    query_estimate = "select count_stat('%s')" % query_eval.replace("'", "''")
                    cr.execute(query_estimate)
                    res = cr.fetchone()
                else:
                    query_str = 'SELECT count(1) FROM ' + from_clause + where_str
                    cr.execute(query_str, where_clause_params)
                    res = cr.fetchone()
                return res[0]

            limit_str = limit and ' limit %d' % limit or ''
            offset_str = offset and ' offset %d' % offset or ''
            query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by + limit_str + offset_str
            cr.execute(query_str, where_clause_params)
            res = cr.fetchall()

            # TDE note: with auto_join, we could have several lines about the same result
            # i.e. a lead with several unread messages; we uniquify the result using
            # a fast way to do it while preserving order (http://www.peterbe.com/plog/uniqifiers-benchmark)
            def _uniquify_list(seq):
                seen = set()
                return [x for x in seq if x not in seen and not seen.add(x)]

            return _uniquify_list([x[0] for x in res])

        def refresh_stat(self,cr, from_clause):

            query_str = "select count(1) from pg_stat_activity where query ilike '%%analyze%%' and query ilike '%%%s%%' " \
                        "and query not " \
                        "ilike 'select count(1) from pg_stat_activity where query ilike ''%%analyze%%'' " \
                        "and query ilike ''%%%s%%''%%'" % (from_clause, from_clause,)

            cr.execute(query_str)
            res = cr.fetchone()
            current_refresh = res[0]
            if current_refresh < 1:
                query_str = 'select extract(epoch from diff) seconds from ' \
                            '(SELECT schemaname, relname, CURRENT_TIMESTAMP-last_analyze as diff ' \
                            'FROM pg_stat_all_tables WHERE relname = %s) t'
                cr.execute(query_str, (from_clause,))
                res = cr.fetchone()
                if res:
                    interval_stat = res[0]
                    if interval_stat > 60:
                        query_str = 'analyze %s' % from_clause
                        cr.execute(query_str)

        if not hasattr(openerp.models.BaseModel, "odoo_orm_improved_monkey_done"):
            cr.execute('SELECT proname FROM pg_proc WHERE proname = %s', ('count_stat',))
            if not cr.fetchone():
                cr.execute("""
CREATE or REPLACE FUNCTION count_stat(query text) RETURNS INTEGER AS
$func$
DECLARE
    rec   record;
    ROWS  INTEGER;
BEGIN
    FOR rec IN EXECUTE 'EXPLAIN ' || query LOOP
        ROWS := SUBSTRING(rec."QUERY PLAN" FROM ' rows=([[:digit:]]+)');
        EXIT WHEN ROWS IS NOT NULL;
    END LOOP;
 
    RETURN ROWS;
END
$func$ LANGUAGE plpgsql
                """)
                cr.commit()
                cr.execute("set enable_seqscan=off");
            openerp.models.BaseModel.odoo_orm_improved_monkey_done = True
            openerp.models.BaseModel._search = _search_custom
            openerp.models.BaseModel.refresh_stat = refresh_stat
        super(BaseModelExtend, self).__init__(pool, cr)
