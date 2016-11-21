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

from openerp import models, api, fields
from openerp.exceptions import UserError


class GenerateTrackingLabelsWizard(models.TransientModel):
    _name = 'generate.tracking.labels.wizard'

    transporter_id = fields.Many2one('tracking.transporter', string=u"Transporteur")
    direction = fields.Selection([('to_customer', "Va vers le client"), ('from_customer', "Vient du client")],
                                 required=True)
    type = fields.Selection([('france', "France (ou OM)"), ('alien', "Etranger")], string=u"Type d'envoi",
                            required=True, default='france')
    save_tracking_number = fields.Boolean(string=u"Enregistrer le numéro de suivi pour l'objet courant", default=True)
    transportation_amount = fields.Float(string=u"Prix du transport", help=u"En euros")
    total_amount = fields.Float(string=u"Prix TTC de l’envoi", help=u"En euros")
    sender_parcel_ref = fields.Char(string=u"Référence client",
                                    help=u"Numéro de commande tel que renseigné dans votre SI. Peut être utile pour "
                                         u"rechercher des colis selon ce champ sur le suivi ColiView (apparaît dans le "
                                         u"champ 'Réf. client')")
    sale_order_id = fields.Many2one('sale.order', string=u"Commande client")
    partner_id = fields.Many2one('res.partner', string=u"Adresse")
    company_name = fields.Char(string=u"Raison sociale", required=True)
    last_name = fields.Char(string=u"Nom", required=True)
    first_name = fields.Char(string=u"Prénom", required=True)
    line0 = fields.Char(string=u"Etage, couloir, escalier, appartement")
    line1 = fields.Char(string=u"Entrée, bâtiment, immeuble, résidence")
    line2 = fields.Char(string=u"Numéro et libellé de voie. ", required=True)
    line3 = fields.Char(string=u"Lieu dit ou autre mention")
    country_id = fields.Many2one('res.country', string=u"Pays")
    city = fields.Char(string=u"Ville", required=True)
    zip = fields.Char(string=u"Code postal", required=True)
    phone_number = fields.Char(string=u"Tél")
    mobile_number = fields.Char(string=u"Mobile")
    door_code1 = fields.Char(string=u"Code porte 1")
    door_code2 = fields.Char(string=u"Code porte 2")
    email = fields.Char(string=u"Email", required=True)
    intercom = fields.Char(string=u"Interphone")
    language = fields.Char(string=u"Langue", default='FR', required=True)
    adressee_parcel_ref = fields.Char(string=u"Référence colis pour destinataire")
    code_bar_for_reference = fields.Selection([('false', 'Non'), ('true', 'Oui')], string=u"Afficher code barre",
                                           default='false', help=u"Pour les bordereaux retours uniquement")
    service_info = fields.Char(string=u"Nom du service de réception retour",
                              help=u"Pour les bordereaux retours uniquement")
    instructions = fields.Char(string=u"Motif du retour")
    weight = fields.Float(string=u"Poids du colis", required=True, help=u"En kg")
    output_printing_type_id = fields.Many2one('output.printing.type', string=u"Format de l'étiquette")
    return_type_choice = fields.Selection([('2', u"Retour payant en prioritaire"),
                                         ('3', u"Ne pas retourner")],
                                        string=u"Retour à l'expéditeur", default='3')
    produit_expedition_id = fields.Many2one('type.produit.expedition', string=u"Produit souhaité", required=True)
    non_machinable = fields.Selection([('false', "Dimensions standards"),
                                      ('true', "Dimensions non standards")],
                                     string="Dimensions", default='false')
    ftd = fields.Selection([('false', "Auto"), ('true', "Manuel")],
                           string=u"Droits de douane", default='false',
                           help=u"Sélectionnez manuel vous souhaitez prendre à votre charge les droits de douanes en "
                                u"cas de taxation des colis")

    @api.onchange('sale_order_id')
    def onchange_sale_order_id(self):
        self.ensure_one()
        if self.sale_order_id:
            self.partner_id = self.sale_order_id.partner_shipping_id
            self.weight = sum([l.product_id.weight * l.product_uom_qty for l in self.sale_order_id.order_line]) or 1
            self.transportation_amount = (self.sale_order_id and int(self.sale_order_id.amount_total)) or 0
            self.total_amount = (self.sale_order_id and int(self.sale_order_id.amount_untaxed)) or 0
            self.sender_parcel_ref = (self.sale_order_id and self.sale_order_id.name) or ''

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.ensure_one()
        if self.partner_id:
            self.country_id = self.partner_id.country_id
            self.company_name = self.partner_id.name
            self.last_name = self.partner_id.name and ' '.join(self.partner_id.name.split(' ')[1:]) or False
            self.first_name = self.partner_id.name and self.partner_id.name.split(' ')[0] or False
            self.line2 = self.partner_id.street or ''
            self.line3 = self.partner_id.street2 or ''
            self.city = self.partner_id.city or ''
            self.zip = self.partner_id.zip or ''
            self.phone_number = (self.partner_id.phone and self.partner_id.phone.replace(' ', '').replace('-', '') or '')
            self.mobile_number = self.partner_id.mobile or ''
            self.email = self.partner_id.email or ''

    @api.onchange('country_id')
    def onchange_country_id(self):
        self.ensure_one()
        if self.country_id:
            self.type = self.partner_id.country_id.code == 'FR' and 'france' or 'alien'

    # A few functions to overwrite
    @api.multi
    def get_output_file(self, direction):
        return u"Etiquette d'envoi"

    @api.multi
    def create_attachment(self, outputfile, direction, file=False, pdf_binary_string=False):
        return False

    @api.multi
    def generate_label(self):
        self.ensure_one()
        if self.output_printing_type_id.transporter_id != self.transporter_id:
            raise UserError(u"Format %s inconnu pour le transporteur %s" %
                            (self.output_printing_type_id.name, self.transporter_id.name))
        elif self.produit_expedition_id.transporter_id != self.transporter_id:
            raise UserError(u"Produit %s inconnu pour le transporteur %s" %
                            (self.produit_expedition_id.name, self.transporter_id.name))
        return [''] * 4


class TypeProduitExpedition(models.Model):
    _name = 'type.produit.expedition'

    name = fields.Char(string=u"Type de bordereau", readonly=True)
    transporter_id = fields.Many2one('tracking.transporter', string=u"Transporteur")
    code = fields.Char(string=u"Code Transporteur", readonly=True)
    used_from_customer = fields.Boolean(string=u"Utilisé pour les retours depuis le client")
    used_to_customer = fields.Boolean(string=u"Utilisé pour les envois vers le client")
    used_on_demand = fields.Boolean(string=u"Utilisé à la carte", compute='_compute_used_on_demand', store=True)

    @api.depends('used_from_customer', 'used_to_customer')
    def _compute_used_on_demand(self):
        for rec in self:
            rec.used_on_demand = rec.used_from_customer or rec.used_to_customer


class GenerateLabelOutputPrintingType(models.Model):
    _name = 'output.printing.type'

    name = fields.Char(string=u"Format de sortie", readonly=True)
    transporter_id = fields.Many2one('tracking.transporter', string=u"Transporteur")
    code = fields.Char(string=u"Code Transporteur", readonly=True)
