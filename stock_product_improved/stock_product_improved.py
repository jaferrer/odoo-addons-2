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

from openerp import models, api, _


class ProductLabelProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def open_moves_for_product(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['search_default_done'] = True
        ctx['search_default_product_id'] = self.id
        ctx['default_product_id'] = self.id
        return {
            'name': _("Moves for product %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'domain': ['|', ('location_id.company_id', '=', False),
                       ('location_id.company_id', 'child_of', self.env.user.company_id.id),
                       '|', ('location_dest_id.company_id', '=', False),
                       ('location_dest_id.company_id', 'child_of', self.env.user.company_id.id)],
            'context': ctx,
        }
