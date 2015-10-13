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
#

from openerp import fields, models, api, _


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    product_parent_id = fields.Many2one('product.template', string="Parent Product",
                                        compute='_compute_parents')
    father_line_ids = fields.Many2many('mrp.bom.line', 'mrp_bom_lines_father_rel', 'child_id', 'father_id',
                                       compute="_compute_parents")

    @api.multi
    @api.depends('bom_id.product_id', 'bom_id.product_tmpl_id', 'bom_id')
    def _compute_parents(self):
        """Computes the fields necessary to get use cases."""
        for rec in self:
            parent_product = rec.bom_id.product_id
            parent_product_tmpl = rec.bom_id.product_tmpl_id
            rec.product_parent_id = parent_product.product_tmpl_id or parent_product_tmpl

            if parent_product:
                products = parent_product
            else:
                products = self.env['product.product'].search([('product_tmpl_id', '=', parent_product_tmpl.id)])
            if self.env.context.get('date_report_use_cases'):
                date_report = self.env.context['date_report_use_cases']
                parent_lines = self.search(
                    [('product_id', 'in', products.ids),
                     '|', ('bom_id.date_start', '<=', date_report), ('bom_id.date_start', '=', False),
                     '|', ('bom_id.date_stop', '>=', date_report), ('bom_id.date_start', '=', False)]
                )
            else:
                parent_lines = self.search(
                    [('product_id', 'in', products.ids),
                     '|', ('bom_id.date_start', '<=', fields.Date.today()), ('bom_id.date_start', '=', False),
                     '|', ('bom_id.date_stop', '>=', fields.Date.today()), ('bom_id.date_start', '=', False)]
                )

            rec.father_line_ids = [(6, 0, [p.id for p in parent_lines])]

    @api.multi
    def explode(self, bom_lines_done, qty, date):
        self.ensure_one()
        list_qty = []
        bom_lines = self.with_context(date_report_use_cases=date).father_line_ids
        for line in bom_lines_done:
            if line in bom_lines:
                bom_lines = bom_lines - line
        bom_lines_done = bom_lines_done + bom_lines
        while bom_lines:
            current_parent_product = bom_lines[0].product_parent_id
            bom_lines_current_product = bom_lines.filtered(lambda l: l.product_parent_id == current_parent_product)
            while bom_lines_current_product:
                bom_lines_current_bom = bom_lines_current_product.\
                    filtered(lambda l: l.bom_id == bom_lines_current_product[0].bom_id)
                list_qty += [{'to_check': True,
                              'line_ids': bom_lines_current_bom,
                              'qty': qty * sum([float(x.product_qty) / x.bom_id.product_qty for x in bom_lines_current_bom]),
                              'product_id': current_parent_product,
                              'bom_id': bom_lines_current_product[0].bom_id}]
                bom_lines_current_product = bom_lines_current_product - bom_lines_current_bom
                bom_lines = bom_lines - bom_lines_current_bom
        return list_qty, bom_lines_done


class ProductProduct(models.Model):
    _inherit = 'product.product'

    use_case_count = fields.Integer("No of use cases", compute='_compute_use_case_count')

    @api.multi
    def _compute_use_case_count(self):
        for rec in self:
            rec.use_case_count = len(self.env['mrp.bom.line'].search(
                [('product_id', '=', rec.id),
                 '|', ('bom_id.date_start', '<=', fields.Date.today()), ('bom_id.date_start', '=', False),
                 '|', ('bom_id.date_stop', '>=', fields.Date.today()), ('bom_id.date_start', '=', False)])
            )


class SirailDefinitionDateCasEmploi(models.TransientModel):
    _name = 'date.report.use.cases'

    def _get_default_product_id(self):
        if self.env.context.get('active_id'):
            return self.env['product.product'].search([('id', '=', self.env.context.get('active_id'))])
        else:
            return False

    product_id = fields.Many2one('product.product', string='Related product', default=_get_default_product_id, required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today())
