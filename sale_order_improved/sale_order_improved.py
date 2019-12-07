# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import api, fields, models


class SaleOrderImproved(models.Model):
    _inherit = 'sale.order'

    route_id = fields.Many2one('stock.location.route', u"Route", domain=[('sale_selectable', '=', True)],
                               help=u"Route d'approvisionnement des lignes de commande")

    @api.multi
    @api.onchange('route_id')
    def onchange_route_id(self):
        for rec in self:
            for line in rec.order_line:
                line.route_id = rec.route_id


class SaleOrderLineImproved(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):

        if self.route_id and self.route_id.pull_ids:
            src_location = self.route_id.pull_ids.mapped('location_src_id')
            if src_location:
                self.env.context = self.with_context(location=src_location[0].id).env.context

        return super(SaleOrderLineImproved, self)._onchange_product_id_check_availability()
