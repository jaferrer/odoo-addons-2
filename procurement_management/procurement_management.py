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

from openerp import fields, models, api


class ProcurementManagementStockMove(models.Model):
    _inherit = 'stock.move'

    cancel_date = fields.Datetime(string=u"Cancel date")
    cancel_uid = fields.Many2one('res.users', string=u"Cancel user")

    @api.model
    def _create_procurements(self, moves):
        not_cancelled_procurements = self.env['procurement.order'].search([('move_dest_id', 'in', moves.ids),
                                                                           ('state', '!=', 'cancel')])
        to_process = self.search([('state', 'not in', ['done', 'cancel']),
                                  ('product_id.type', '!=', 'service'),
                                  ('id', 'in', moves.ids),
                                  ('id', 'not in', [proc.move_dest_id.id for proc in not_cancelled_procurements])])
        return super(ProcurementManagementStockMove, self)._create_procurements(to_process)

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'cancel':
            vals['cancel_date'] = fields.Datetime.now()
            vals['cancel_uid'] = self.env.user.id
        return super(ProcurementManagementStockMove, self).write(vals)
