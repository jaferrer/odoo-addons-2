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
def job_compute_father_line_ids(session, model_name, context):
    bom_line_model = session.env[model_name].with_context(context)
    bom_line_model.compute_father_line_ids()
    return "End update"


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    product_parent_id = fields.Many2one('product.product', string=u"Parent Product",
                                        related='bom_id.product_id')
    father_line_ids = fields.Many2many('mrp.bom.line', 'mrp_bom_lines_father_rel', 'child_id', 'father_id',
                                       string=u"Father lines")

    @api.model
    def cron_compute_father_line_ids(self):
        job_compute_father_line_ids.delay(ConnectorSession.from_env(self.env), 'mrp.bom.line',
                                              dict(self.env.context), description=u"Update father lines for bom lines")

    @api.model
    def compute_father_line_ids(self):
        self.env.cr.execute("""TRUNCATE mrp_bom_lines_father_rel;""")
        self.env.cr.execute("""INSERT INTO mrp_bom_lines_father_rel
(child_id,
father_id)

  WITH bom_line_modified AS (
    SELECT
      line.*,
      pp.product_tmpl_id
    FROM mrp_bom_line line
      LEFT JOIN product_product pp ON pp.id = line.product_id),

    mrp_bom_restricted AS (
      SELECT *
      FROM mrp_bom
      WHERE (date_start IS NULL OR date_start <= current_timestamp) AND
            (date_stop IS NULL OR date_stop >= current_timestamp))

SELECT
  line.id        AS child_id,
  parent_line.id AS father_id
FROM mrp_bom_line line
  LEFT JOIN mrp_bom bom ON bom.id = line.bom_id
  LEFT JOIN bom_line_modified parent_line ON (bom.product_id IS NOT NULL AND parent_line.product_id = bom.product_id) OR
                                             (bom.product_id IS NULL AND
                                              parent_line.product_tmpl_id = bom.product_tmpl_id)
  INNER JOIN mrp_bom_restricted bom_restricted ON bom_restricted.id = parent_line.bom_id
GROUP BY line.id, parent_line.id;""")


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
