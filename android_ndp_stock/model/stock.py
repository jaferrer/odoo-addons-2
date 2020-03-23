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

from odoo import models, fields

SELECTION_TCB_TYPE = [
    ('put_in_stock', u"Rangement"),
    ('put_out_of_stock', u"Sortie de Stock"),
    ('not_managed', u"Non Utilisé"),
]


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    tcb_type = fields.Selection(SELECTION_TCB_TYPE, string=u"Type TCB", default="not_managed",
                                help=u"Type de Transfert Pour l'application android")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_picking_operation_ids = fields.One2many('tcb.stock.picking.operation', 'picking_id')


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    stock_picking_operation_ids = fields.One2many('tcb.stock.picking.operation', 'picking_id')
