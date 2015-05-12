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

class res_partner_purchase_supplier_stat (models.Model):
    """ajout de champs dans la table res.partner"""
    _inherit = 'res.partner'

    total_purchase = fields.Float("Total des factures",compute="_calcule_total_facture",help="Total des factures achats pour un fournisseur")

    @api.multi
    def _calcule_total_facture(self):
        for rec in self:
            compte_total_facture = rec.env['account.invoce.line'].search([('invoce_id.type','=','in_invoce'),
                                                                              ('invoce_id.partner.id.','=',rec.id),])

            compte_total_avoir = rec.env['account.invoce.line'].search([('invoce_id.type','=','in_refund'),
                                                                              ('invoce_id.partner.id.','=',rec.id),])
            total_facture = 0
            total_avoir = 0

            for ligne_facture in compte_total_facture:
                total_facture += ligne_facture.price_subtotal

            for ligne_avoir in compte_total_avoir:
                total_avoir += ligne_avoir.price_subtotal

            rec.total_purchase = total_facture - total_avoir

