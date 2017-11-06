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

from openerp import fields, models, api
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


@job
def job_compute_use_case_count(session, model_name, product_ids, context):
    products = session.env[model_name].with_context(context).browse(product_ids)
    products.compute_use_case_count()
    return "End update"


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    product_parent_id = fields.Many2one('product.product', string="Parent Product",
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
            rec.product_parent_id = parent_product

            if parent_product:
                products = parent_product
            else:
                products = self.env['product.product'].search([('product_tmpl_id', '=', parent_product_tmpl.id)])
            date_report = self.env.context.get('date_report_use_cases') or fields.Date.today()
            parent_lines = self.search(
                [('product_id', 'in', products.ids),
                 '|', ('bom_id.date_start', '<=', date_report), ('bom_id.date_start', '=', False),
                 '|', ('bom_id.date_stop', '>=', date_report), ('bom_id.date_start', '=', False)]
            )

            rec.father_line_ids = [(6, 0, [p.id for p in parent_lines])]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    use_case_count = fields.Integer("Number of use cases", readonly=True)

    @api.multi
    def compute_use_case_count(self):
        for rec in self:
            rec.use_case_count = len(self.env['mrp.bom.line'].search(
                [('product_id', '=', rec.id),
                 ('bom_id.active', '=', True),
                 '|', ('bom_id.date_start', '<=', fields.Date.today()), ('bom_id.date_start', '=', False),
                 '|', ('bom_id.date_stop', '>=', fields.Date.today()), ('bom_id.date_start', '=', False)])
            )

    @api.model
    def cron_compute_use_case_count(self):
        products = self.search(['|', ('active', '=', False), ('active', '=', True)])
        chunk_number = 0
        while products:
            chunk_products = products[:100]
            chunk_number += 1
            job_compute_use_case_count.delay(ConnectorSession.from_env(self.env), 'product.product', chunk_products.ids,
                                             dict(self.env.context),
                                             description=u"Update number of use cases (chunk %s)" % chunk_number)
            products = products[100:]
