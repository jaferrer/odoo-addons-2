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
from lxml import etree

from odoo import models, api
from odoo.tools.safe_eval import safe_eval


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_aggregates(self, domain, statistics):
        """Returns a list of aggregated values

        :param domain: Odoo Domain
        :param statistics: dict {
            "aggregate_name': {
                'field': field name to aggregate
                'group_operator': sql func
                'name': aggregate name
                'string': display label
            },
            "formula_name": {
                'name': formula name
                'string": display label
                'value': formula
            }
            "other_aggregate": {...}
        }
        :return: dict {
            "aggregate_name": value,
            "other_aggregate": {...},
            "formula_name": value,
            "other_formula": {...},
        }
        """
        self.check_access_rights('read')
        where = self._where_calc(domain)
        self._apply_ir_rules(where, 'read')

        def prefix_terms(prefix, terms):
            return (prefix + " " + ",".join(terms)) if terms else ''

        def prefix_term(prefix, term):
            return ('%s %s' % (prefix, term)) if term else ''

        aggregates = {k: v for k, v in statistics.iteritems() if not v.get('formula')}
        formulas = {k: v for k, v in statistics.iteritems() if v.get('formula')}

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
        res = dict(zip([a['name'] for a in aggregates.values()], [r or 0 for r in res]))
        eval_context = res.copy()
        for formula in formulas.values():
            eval_context[formula['name']] = safe_eval(formula['formula'], eval_context)
            res[formula['name']] = eval_context[formula['name']]
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Base, self).fields_view_get(view_id, view_type, toolbar, submenu)
        if res['type'] == 'analysis':
            doc = etree.fromstring(res['arch'])
            for view in doc.iter('view'):
                if view.get('ref'):
                    view.set('view_id', str(self.env.ref(view.get('ref')).id))
            res['arch'] = etree.tostring(doc, encoding="utf-8").replace('\t', '')
        return res
