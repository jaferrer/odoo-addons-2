# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models, fields, api


class StockPickTypeWebUiAction(models.Model):
    _name = 'stock.picking.type.web.ui.action'
    _description = "Assistant Web pour les Pickings"

    name = fields.Char(u"Name", required=True)
    action = fields.Char(u"Action", required=True)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    web_action_id = fields.Many2one('stock.picking.type.web.ui.action', u"Barcode App")

    @api.multi
    def web_ui_launch_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': "/web_ui_stock/web/?action=%s&picking_type_id=%s" % (self.web_action_id.action, self.id),
            'target': 'self'
        }
