# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_aggregates(self, domain, aggregates):
        """Returns a list of aggregated values

        :param domain: Odoo Domain
        :param aggregates: dict {
            "aggregate_name': {
                'field': field name to aggregate
                'group_operator': sql func
                'name': aggregate name
                'string': display label
            },
            "other_aggregate": {...}
        }
        :return: dict {
            "aggregate_name": value,
            "other_aggregate": {...},
        }
        """
        self.check_access_rights('read')
        where = self._where_calc(domain)
        self._apply_ir_rules(where, 'read')

        def prefix_terms(prefix, terms):
            return (prefix + " " + ",".join(terms)) if terms else ''

        def prefix_term(prefix, term):
            return ('%s %s' % (prefix, term)) if term else ''

        select_terms = []
        for agg in aggregates.values():
            group_operator = agg.get('group_operator')
            if not group_operator:
                field_def = self._fields[agg['field']]
                group_operator = field_def.group_operator
                if field_def.type == 'many2one':
                    group_operator = 'count_distinct'
            if group_operator == 'count_distinct':
                select_terms.append('COUNT(DISTINCT %s) AS "%s"' % (agg['field'], agg['name']))
            else:
                select_terms.append('%s(%s) AS "%s"' % (group_operator, agg['field'], agg['name']))

        from_clause, where_clause, where_clause_params = where.get_sql()
        query = """
            SELECT %(extra_fields)s
            FROM %(from)s
            %(where)s
        """ % {
            'table': self._table,
            'extra_fields': prefix_terms('', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
        }
        self.env.cr.execute(query, where_clause_params)
        res = self.env.cr.fetchone()
        res = dict(zip([a['name'] for a in aggregates.values()], res))
        return res
