# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ConfirmPeriodWizard(models.TransientModel):
    _inherit = 'confirm.period.wizard'

    @api.multi
    def confirm_sale_forecast(self):
        self.ensure_one()
        # Récupération des lignes sale_planning correspondant à season + year
        # Création d'une liste si sale_qty+reserve_qty > 0
        sale_plannings = self.period_id.sale_planning_ids.filtered(lambda r: (r.sale_qty + r.reserve_qty > 0))
        # Méthode récursive où on créé une map <materiel, qté>
        dict_product = {}
        for planning in sale_plannings:
            product_id = planning.product_id
            planning_quantity = planning.sale_qty + planning.reserve_qty
            _, products = product_id.bom_ids[:1].recursive_explode(product_id, planning_quantity)
            for product, quantity in products:
                dict_product.setdefault(product, 0)
                dict_product[product] += quantity
        # Création des purchase_planning associé
        purchase_plannings = self.env['purchase.planning']
        purchase_plannings |= self.env['purchase.planning'].create([{
            'period_id': self.period_id.id,
            'product_id': prod.id,
            'supplier_id': prod.seller_ids[:1].id,
            'retained_qty': dict_res,
        } for prod, dict_res in dict_product.items()])
        # Changement de status des sale_planning de la periode
        self.period_id.sale_planning_ids.write({'state': 'confirm'})
        self.period_id.write({'sale_state': 'confirm'})
        # Redirection vers les lignes que l'on vient de créer
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Forecast',
            'res_model': 'purchase.planning',
            'view_type': 'form',
            'view_mode': 'tree',
            'context': self.env.context,
            'domain': [('period_id', '=', self.period_id.id)],
        }
