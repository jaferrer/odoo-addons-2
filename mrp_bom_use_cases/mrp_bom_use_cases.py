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

from odoo import fields, models, api
from odoo.addons.queue_job.job import job


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    product_parent_id = fields.Many2one('product.product', string=u"Parent Product", related='bom_id.product_id')
    father_line_ids = fields.Many2many('mrp.bom.line', 'mrp_bom_lines_father_rel', 'child_id', 'father_id',
                                       string=u"Father lines")
    type = fields.Selection(related='bom_id.type')

    @api.model
    def cron_compute_father_line_ids(self):
        self.with_delay().compute_father_line_ids()

    @job
    @api.model
    def compute_father_line_ids(self):
        self.env.cr.execute("""TRUNCATE mrp_bom_lines_father_rel;""")
        self.env.cr.execute("""INSERT INTO mrp_bom_lines_father_rel (child_id, father_id)

  WITH bom_line_modified AS (
    SELECT
      line.*,
      pp.product_tmpl_id
    FROM mrp_bom_line line
      LEFT JOIN product_product pp ON pp.id = line.product_id)

SELECT
  line.id        AS child_id,
  parent_line.id AS father_id
FROM mrp_bom_line line
  LEFT JOIN mrp_bom bom ON bom.id = line.bom_id
  LEFT JOIN bom_line_modified parent_line ON (bom.product_id IS NOT NULL AND parent_line.product_id = bom.product_id) OR
                                             (bom.product_id IS NULL AND
                                              parent_line.product_tmpl_id = bom.product_tmpl_id)
GROUP BY line.id, parent_line.id;""")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_case_count = fields.Integer("Number of use cases", readonly=True)

    @job
    @api.multi
    def compute_use_case_count(self):
        for rec in self:
            rec.use_case_count = len(self.env['mrp.bom.line'].search([
                ('product_id', 'in', rec.product_variant_ids.ids),
                ('bom_id.active', '=', True),
            ]))

    @api.model
    def cron_compute_use_case_count(self):
        products = self.search(['|', ('active', '=', False), ('active', '=', True)])
        chunk_number = 0
        while products:
            chunk_products = products[:100]
            chunk_number += 1
            chunk_products.with_delay().compute_use_case_count()
            products = products[100:]
