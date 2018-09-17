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


@job
def job_compute_father_line_ids(session, model_name, bom_line_ids, context):
    products = session.env[model_name].with_context(context).browse(bom_line_ids)
    products.compute_father_line_ids()
    return "End update"


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    product_parent_id = fields.Many2one('product.product', string=u"Parent Product",
                                        related='bom_id.product_id')
    father_line_ids = fields.Many2many('mrp.bom.line', 'mrp_bom_lines_father_rel', 'child_id', 'father_id',
                                       string=u"Father lines")

    @api.model
    def cron_compute_father_line_ids(self):
        lines = self.search([])
        chunk_number = 0
        while lines:
            chunk_lines = lines[:100]
            chunk_number += 1
            job_compute_father_line_ids.delay(ConnectorSession.from_env(self.env), 'mrp.bom.line', chunk_lines.ids,
                                              dict(self.env.context),
                                              description=u"Update father lines for bom lines (chunk %s)" %
                                                          chunk_number)
            lines = lines[100:]

    @api.multi
    def compute_father_line_ids(self):
        date_today = fields.Date.today()
        active_boms = self.env['mrp.bom'].search(['|', ('date_start', '<=', date_today), ('date_start', '=', False),
                                                  '|', ('date_stop', '>=', date_today), ('date_start', '=', False)])
        for rec in self:
            products = rec.product_parent_id or self.env['product.product']. \
                search([('product_tmpl_id', '=', rec.bom_id.product_tmpl_id.id)])
            parent_lines = self.search([('product_id', 'in', products.ids), ('bom_id', 'in', active_boms.ids)])
            rec.father_line_ids = [(6, 0, parent_lines.ids)]


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
