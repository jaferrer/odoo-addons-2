# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.report import report_sxw


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'report_use_cases': self.report_use_cases,
        })

    def report_use_cases(self, wizard):
        wizard.ensure_one()
        main_bom_id = self.pool.get('mrp.bom')._bom_find(self.cr, self.uid,
                                                 product_tmpl_id=wizard.product_id.product_tmpl_id.id,
                                                 product_id=wizard.product_id.id)
        main_bom = self.pool.get('mrp.bom').browse(self.cr, self.uid, main_bom_id)
        lignes_rapport = {'default_code': wizard.product_id.default_code,
                          'date': wizard.date,
                          'bom_id': main_bom.name,
                          'qty_per_product': []}
        list_qty = []
        bom_lines = self.pool.get('mrp.bom.line').\
            search(self.cr, self.uid, [('product_id', '=', wizard.product_id.id),
                                       '|', ('bom_id.date_start', '<=', wizard.date), ('bom_id.date_start', '=', False),
                                       '|', ('bom_id.date_stop', '>=', wizard.date), ('bom_id.date_start', '=', False)])
        bom_lines = self.pool.get('mrp.bom.line').browse(self.cr, self.uid, bom_lines)

        # First, group lines by BOM
        bom_lines_done = bom_lines
        while bom_lines:
            bom_lines_same_bom = bom_lines.filtered(lambda x: x.bom_id == bom_lines[0].bom_id)
            list_qty += [{'to_check': True,
                          'line_ids': bom_lines_same_bom,
                          'qty': float(sum([x.product_qty for x in bom_lines_same_bom])) /
                                 bom_lines[0].bom_id.product_qty,
                          'product_id': bom_lines[0].product_parent_id,
                          'bom_id': bom_lines[0].bom_id}]
            bom_lines = bom_lines - bom_lines_same_bom

        # Next, exploding bom lines one by one
        while [x for x in list_qty if x.get('to_check')]:
            first_not_checked_list = [x for x in list_qty if x.get('to_check')][0]
            explode, bom_lines_done = first_not_checked_list['line_ids'][0].\
                explode(bom_lines_done, first_not_checked_list['qty'], wizard.date)
            if explode:
                list_qty += explode
            first_not_checked_list['to_check'] = False

        # Grouping by BOM
        result = []
        list_bom_done = []
        for checked_list in [x for x in list_qty if x['bom_id'] not in list_bom_done]:
            if checked_list.get('bom_id') not in list_bom_done:
                result += [{'product': checked_list['product_id'].name,
                            'bom': checked_list['bom_id'].name,
                            'qty': sum(x['qty'] for x in list_qty if x['bom_id'] == checked_list['bom_id'])}]
                list_bom_done += checked_list['bom_id']
        lignes_rapport['qty_per_product'] = sorted(result, key=lambda x: x['bom'])
        return lignes_rapport
