# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class JitResPartner(models.Model):
    _inherit = 'res.partner'

    order_group_period = fields.Many2one('procurement.time.frame', string="Order grouping period",
                                         help="Select here the time frame by which orders line placed to this supplier"
                                              " should be grouped by PO. This is value should be set to the typical "
                                              "delay between two orders to this supplier.")
    nb_max_draft_orders = fields.Integer(string="Maximal number of draft purchase orders",
                                         help="Used by the purchase planner to generate draft orders")
    nb_draft_orders = fields.Integer(string="Number of draft purchase orders",
                                     help="Used by the purchase planner to generate draft orders",
                                     compute='_compute_nb_draft_orders')

    @api.multi
    def _compute_nb_draft_orders(self):
        for rec in self:
            draft_orders = self.env['purchase.order'].search([('partner_id', '=', rec.id),
                                                              ('state', '=', 'draft')])
            draft_orders = draft_orders.filtered(lambda order: order.order_line)
            rec.nb_draft_orders = len(draft_orders)
