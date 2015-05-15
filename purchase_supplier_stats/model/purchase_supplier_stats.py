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
    total_sale_supplier = fields.Float("Total des ventes",compute="_calcul_total_vente_article", help="Total des ventes")
    total_purchase_order = fields.Float("Total des commandes en cours",compute="_calcul_total_commande",help="commande en cours")

    @api.multi
    def _calcule_total_facture(self):
        for rec in self:
            compte_total_facture = rec.env['account.invoice.line'].search([('invoice_id.state','in',['open','paid']),
                                                                            ('invoice_id.type','=','in_invoice'),
                                                                            ('invoice_id.partner_id','=',rec.id),])

            compte_total_avoir = rec.env['account.invoice.line'].search([('invoice_id.state','in',['open','paid']),
                                                                            ('invoice_id.type','=','in_refund'),
                                                                            ('invoice_id.partner_id','=',rec.id),])

            total_facture = 0
            total_avoir = 0

            for ligne_facture in compte_total_facture:
                total_facture += ligne_facture.price_subtotal

            for ligne_avoir in compte_total_avoir:
                total_avoir += ligne_avoir.price_subtotal

            rec.total_purchase = total_facture - total_avoir


    def _calcul_total_vente_article(self):
        for rec in self:
            total_vente_article = rec.env['account.invoice.line'].search([('invoice_id.type','=','out_invoice'),
                                                                          ('invoice_id.state','in',['open','paid']),
                                                                          ('product_id.product_tmpl_id.seller_id','=',rec.id),])

            total_vente_article_avoir = rec.env['account.invoice.line'].search([('invoice_id.type','=','out_refund'),
                                                                                ('invoice_id.state','in',['open','paid']),
                                                                            ('product_id.product_tmpl_id.seller_id','=',rec.id),])
            print total_vente_article

            total_vente_article
            total_facture = 0
            total_avoir = 0

            for ligne_facture in total_vente_article:
                total_facture += ligne_facture.price_subtotal

            for ligne_avoir in total_vente_article_avoir:
                total_avoir += ligne_avoir.price_subtotal

            rec.total_sale_supplier = total_facture - total_avoir


    def _calcul_total_commande(self):
        for rec in self:
            total_commandes = rec.env['purchase.order.line'].search([('order_id.state','in',['approved','picking_in_progress','confirmed',
                                                                                             'picking_done','except_picking','except_invoice']),
                                                                          ('partner_id','=',rec.id),])

            total_commande = 0

            for ligne_commande in total_commandes:
                total_commande += ligne_commande.price_subtotal

            rec.total_purchase_order = total_commande






