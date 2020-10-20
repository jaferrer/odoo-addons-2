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

from openerp import models, api


class MoUpdateMrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def get_orders_to_update(self):
        return self.search([('id', 'in', self.ids),
                            ('backorder_id', '=', False),
                            ('state', 'not in', ['draft', 'done', 'cancel'])])

    @api.model
    def action_produce(self, production_id, production_qty, production_mode, wiz=False):
        result = super(MoUpdateMrpProduction, self).action_produce(production_id, production_qty,
                                                                   production_mode, wiz=wiz)
        production = self.browse(production_id)
        if production.state not in ['done', 'cancel']:
            production.update_moves()
        return result
