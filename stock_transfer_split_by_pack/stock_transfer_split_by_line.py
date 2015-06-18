# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp

class stock_transfer_split_by_pack(models.TransientModel):
    _name = 'stock.transfer.split_by_pack'
    _description = "Split by pack wizard"

    pack_qty = fields.Float("Quantity to set on each line", digits=dp.get_precision('Product Unit of Measure'),
                            required=True)
    create_pack = fields.Boolean("Create a pack for each line")

    @api.multi
    def split_by_pack(self):
        self.ensure_one()
        assert self.env.context.get('active_model') == 'stock.transfer_details_items', 'Wrong underlying model'
        trf_line = self.env['stock.transfer_details_items'].browse(self.env.context['active_id'])
        pack_qty = self[0].pack_qty
        if pack_qty > 0:
            if pack_qty >= trf_line.quantity:
                raise Warning(_("The Quantity to extract (%s) cannot be superior or "
                                "equal to the quantity of the line (%s)") % (pack_qty, trf_line.quantity))
            no_of_packs = int(trf_line.quantity // pack_qty)
            remaining_qty = trf_line.quantity % pack_qty
            no_of_new_packs = no_of_packs if remaining_qty > 0 else no_of_packs - 1
            for i in range(no_of_new_packs):
                new_line = trf_line.copy({'quantity': pack_qty, 'packop_id': False})
                if self[0].create_pack:
                    new_line.put_in_pack()
            action = trf_line.transfer_id.wizard_view()
            if remaining_qty:
                trf_line.quantity = remaining_qty
            else:
                trf_line.quantity = pack_qty
                if self[0].create_pack:
                    trf_line.put_in_pack()


class stock_transfer_split_by_pack2(models.TransientModel):
    _inherit = "stock.transfer_details_items"

#
    @api.multi
    def split_by_pack2(self):

        return {
            'name': _('Split by Configurable'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.transfer.split_by_pack',
            'target': 'popup',
            'views': [(False, 'form')],

            'context': self.env.context,
    }
