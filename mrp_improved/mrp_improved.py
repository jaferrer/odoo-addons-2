# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class ManufacturingOrderPlanningImproved(models.Model):
    _inherit = 'mrp.production'

    procurement_id = fields.Many2one('procurement.order', string="Corresponding procurement order", readonly=True)

    @api.model
    def update_procurement_id(self):
        self.env.cr.execute("""WITH mrp_procurements AS (
    SELECT
        mrp.id     AS mrp_id,
        min(po.id) AS procurement_id
    FROM mrp_production mrp
        LEFT JOIN procurement_order po ON po.production_id = mrp.id
    GROUP BY mrp.id)

SELECT
    mrp.id,
    procs.procurement_id AS new_procurement_id
FROM mrp_production mrp
    LEFT JOIN mrp_procurements procs ON procs.mrp_id = mrp.id
WHERE COALESCE(mrp.procurement_id, 0) != COALESCE(procs.procurement_id, 0)""")
        result = self.env.cr.fetchall()
        for line in result:
            order = self.browse(line[0])
            order.write({'procurement_id': line[1] or False})
