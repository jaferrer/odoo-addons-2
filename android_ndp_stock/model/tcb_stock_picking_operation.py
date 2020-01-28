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
import os

from odoo import api, fields, models, tools, modules
from .stock import SELECTION_TCB_TYPE


class StockPickingOperation(models.Model):
    _name = 'tcb.stock.picking.operation'
    _description = 'Operation de Transfert'
    _auto = False

    def _get_sql_path(self):
        module_path = modules.get_module_path('android_ndp_stock')
        return os.path.join(module_path, 'sql')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        with open(os.path.join(self._get_sql_path(), '%s.sql' % self._name)) as sql_file:
            self.env.cr.execute("""CREATE OR REPLACE VIEW %s AS (%s)""" % (self._table, sql_file.read()))

    picking_batch_id = fields.Many2one('stock.picking.batch', u"Vague de Transfert")
    picking_id = fields.Many2one('stock.picking', u"Bon de Transfert")
    picking_type_id = fields.Many2one('stock.picking.type', u"Type de Transfert")
    product_id = fields.Many2one('stock.location', u"Article")
    loc_src_id = fields.Many2one('stock.location', u"Emplacement source")
    loc_desc_id = fields.Many2one('stock.location', u"Emplacement de destination")
    qty_todo = fields.Float(u"À Faire")
    owner_id = fields.Many2one('res.partner', u"Propriétaire", domain=[('stock_owner', '=', True)])
    user_id = fields.Many2one('res.users', u"Assigné à")
    tcb_type = fields.Selection(SELECTION_TCB_TYPE, string=u"Type TCB", default="not_managed",
                                        help=u"Type de Transfert Pour l'application android")
