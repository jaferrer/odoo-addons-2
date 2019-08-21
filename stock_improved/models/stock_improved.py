# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models, api


class StockPickingImproved(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        """
        Corrige le problème Odoo qui empêche de valider plusieurs pickings en un seul appel.
        Cf ligne 1145 de odoo -> addons -> stock -> models -> stock_move.py
        """

        for rec in self:
            super(StockPickingImproved, rec).action_done()


class StockMoveImproved(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        """
        Corrige le problème Odoo qui empêche de valider plusieurs pickings en un seul appel.
        Cf ligne 1145 de odoo -> addons -> stock -> models -> stock_move.py
        """

        moves_by_picking = {}
        for rec in self:
            moves_by_picking.setdefault(rec.picking_id, self.env['stock.move'])
            moves_by_picking[rec.picking_id] |= rec

        for moves in moves_by_picking.values():
            super(StockMoveImproved, moves).action_done()
