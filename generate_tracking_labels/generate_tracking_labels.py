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

from openerp import models, api, fields, _
from openerp.exceptions import UserError


class GenerateTrackingLabelsWizard(models.TransientModel):
    _name = 'generate.tracking.labels.wizard'

    transporter_id = fields.Many2one('tracking.transporter', u"Transporteur", required=True)
    direction = fields.Selection([
        ('to_customer', "Va vers le client"),
        ('from_customer', "Vient du client")
    ], u"Direction", required=True)
    type = fields.Selection([
        ('france', "France (ou OM)"),
        ('alien', "Etranger")
    ], u"Type d'envoi", required=True, default='france')
    save_tracking_number = fields.Boolean(u"Enregistrer le numéro de suivi pour l'objet courant", default=True)
    transportation_amount = fields.Float(u"Prix du transport", help=u"En euros")
    total_amount = fields.Float(u"Prix TTC de l’envoi", help=u"En euros")
    cod_value = fields.Integer(u"Valeur du contre-remboursement (en centimes €)")
    sender_parcel_ref = fields.Char(u"Référence client",
                                    help=u"Numéro de commande tel que renseigné dans votre SI. Peut être utile pour "
                                         u"rechercher des colis selon ce champ sur le suivi ColiView (apparaît dans le "
                                         u"champ 'Réf. client')")
    customer_parcel_ref = fields.Char(u"Référence Facture client")
    sale_order_id = fields.Many2one('sale.order', u"Commande client")
    partner_orig_id = fields.Many2one('res.partner', u"Expéditeur", required=True)
    partner_id = fields.Many2one('res.partner', u"Adresse", required=True)
    company_name = fields.Char(u"Raison sociale")
    last_name = fields.Char(u"Nom")
    first_name = fields.Char(u"Prénom")
    line0 = fields.Char(u"Etage, couloir, escalier, appartement")
    line1 = fields.Char(u"Entrée, bâtiment, immeuble, résidence")
    line2 = fields.Char(u"Numéro et libellé de voie. ")
    line3 = fields.Char(u"Lieu dit ou autre mention")
    country_id = fields.Many2one('res.country', u"Pays")
    city = fields.Char(u"Ville")
    zip = fields.Char(u"Code postal")
    phone_number = fields.Char(u"Tél")
    mobile_number = fields.Char(u"Mobile")
    door_code1 = fields.Char(u"Code porte 1")
    door_code2 = fields.Char(u"Code porte 2")
    email = fields.Char(u"Email")
    intercom = fields.Char(u"Interphone")
    language = fields.Char(u"Langue", default='FR', required=True)
    adressee_parcel_ref = fields.Char(u"Référence colis pour destinataire")
    code_bar_for_reference = fields.Selection([
        ('false', 'Non'),
        ('true', 'Oui')
    ], u"Afficher code barre", default='false', help=u"Pour les bordereaux retours uniquement")
    service_info = fields.Char(u"Nom du service de réception retour",
                               help=u"Pour les bordereaux retours uniquement")
    instructions = fields.Char(u"Motif du retour")
    weight = fields.Float(u"Poids du colis", required=True, help=u"En kg")
    output_printing_type_id = fields.Many2one('output.printing.type', u"Format de l'étiquette")
    return_type_choice = fields.Selection([
        ('2', u"Retour payant en prioritaire"),
        ('3', u"Ne pas retourner")
    ], u"Retour à l'expéditeur", default='3')
    produit_expedition_id = fields.Many2one('type.produit.expedition', u"Produit souhaité", required=True)
    non_machinable = fields.Selection([
        ('false', "Dimensions standards"),
        ('true', "Dimensions non standards")
    ], u"Dimensions", default='false')
    generate_custom_declaration = fields.Boolean(u"Générer la déclaration douanière")
    content_type_id = fields.Many2one('transporter.content.type', u"Type de marchandise")
    ftd = fields.Selection([('false', "Auto"), ('true', "Manuel")], u"Droits de douane", default='false',
                           help=u"Sélectionnez manuel vous souhaitez prendre à votre charge les droits de douanes en "
                                u"cas de taxation des colis")
    insurance = fields.Boolean(u"Assurance", help=u"Cochez la case pour assurer l'envoi à sa valeur.")

    id_relais = fields.Char(u"Id point relais")

    @api.model
    def create_and_get_action(self, data, act_name=False):
        result = self.create(data)._trigger_onchange()
        default_name = _("%s - New Label for %s") % (result.transporter_id.display_name, result.partner_id.name)
        return {
            'name': act_name or default_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': result._name,
            'res_id': result.id,
            'target': 'new',
            'context': result.env.context,
        }

    @api.model
    def create(self, vals):
        ctx = self.env.context
        produit_expedition_id = vals.get('produit_expedition_id', ctx.get('default_produit_expedition_id'))
        output_printing_type_id = vals.get('output_printing_type_id', ctx.get('default_output_printing_type_id'))
        if not output_printing_type_id and produit_expedition_id:
            trans_product = self.env['type.produit.expedition'].browse(produit_expedition_id)
            vals['output_printing_type_id'] = trans_product.output_printing_type_default_id.id
        return super(GenerateTrackingLabelsWizard, self).create(vals)


    @api.multi
    def _trigger_onchange(self):
        self.ensure_one()
        self.onchange_partner_id()
        self.onchange_transporter_id()
        self.onchange_produit_expedition_id()
        self.onchange_output_printing_type_id()
        self.onchange_country_id()
        return self

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
            self.phone_number = self.partner_id.phone and self.partner_id.phone.replace(' ', '').replace('-', '') or ''
            self.mobile_number = self.partner_id.mobile or ''
            self.email = self.partner_id.email or ''
            self.id_relais = self.partner_id.id_relais

    @api.model
    def is_relais(self, code):
        return False

    @api.onchange('transporter_id')
    def onchange_transporter_id(self):
        self.ensure_one()
        if self.transporter_id:
            if self.output_printing_type_id and self.output_printing_type_id.transporter_id != self.transporter_id:
                self.output_printing_type_id = False
            if self.produit_expedition_id and self.produit_expedition_id.transporter_id != self.transporter_id:
                self.produit_expedition_id = False
            if not self.content_type_id:
                content_type = self.env['transporter.content.type']. \
                    search([('transporter_id', '=', self.transporter_id.id),
                            ('used_by_default', '=', True)], limit=1)
                self.content_type_id = content_type

    @api.onchange('produit_expedition_id')
    def onchange_produit_expedition_id(self):
        self.ensure_one()
        if self.produit_expedition_id:
            if self.output_printing_type_id and \
                    self.produit_expedition_id.transporter_id != self.output_printing_type_id.transporter_id:
                self.output_printing_type_id = False
            if self.transporter_id and self.produit_expedition_id.transporter_id != self.transporter_id:
                self.transporter_id = False

    @api.onchange('output_printing_type_id')
    def onchange_output_printing_type_id(self):
        self.ensure_one()
        if self.output_printing_type_id:
            if self.transporter_id and self.output_printing_type_id.transporter_id != self.transporter_id:
                self.transporter_id = False
            if self.produit_expedition_id and \
                    self.output_printing_type_id.transporter_id != self.produit_expedition_id.transporter_id:
                self.produit_expedition_id = False

    @api.onchange('country_id')
    def onchange_country_id(self):
        self.ensure_one()
        if self.country_id:
            self.type = self.partner_id.country_id.code == 'FR' and 'france' or 'alien'
            self.generate_custom_declaration = self.country_id.force_custom_declaration

    # A few functions to overwrite
    @api.multi
    def get_output_file(self):
        return u"Etiquette d'envoi"

    @api.multi
    def create_attachment(self, list_files=None):
        if not list_files:
            raise UserError(u"Veuillez fournir une pièce jointe à créer")
        return False

    @api.multi
    def get_nb_labels(self):
        return 1

    @api.multi
    def launch_report(self, report):
        return self.env['report'].with_context(active_ids=self.ids).get_action(self, report.report_name)

    @api.multi
    def get_packages_data(self):
        self.ensure_one()
        return [{
            'weight': self.weight or 0,
            'amount_untaxed': self.sale_order_id.amount_untaxed or 0,
            'amount_total': self.sale_order_id.amount_total or 0,
            'cod_value': self.cod_value or 0,
            'height': 0,
            'lenght': 0,
            'width': 0,
        }]

    @api.multi
    def get_order_number(self):
        self.ensure_one()
        return self.sale_order_id.name or ''

    @api.multi
    def get_login_dict(self):
        self.ensure_one()
        return {}

    @api.multi
    def generate_label(self):
        self.ensure_one()
        if self.output_printing_type_id.transporter_id and self.transporter_id and \
                self.output_printing_type_id.transporter_id != self.transporter_id:
            raise UserError(u"Format %s inconnu pour le transporteur %s" %
                            (self.output_printing_type_id.name, self.transporter_id.name))
        if self.produit_expedition_id.transporter_id and self.transporter_id and \
                self.produit_expedition_id.transporter_id != self.transporter_id:
            raise UserError(u"Produit %s inconnu pour le transporteur %s" %
                            (self.produit_expedition_id.name, self.transporter_id.name))
        if self.produit_expedition_id and self.produit_expedition_id.report_id:
            return self.launch_report(self.produit_expedition_id.report_id)
        return []


class TypeProduitExpedition(models.Model):
    _name = 'type.produit.expedition'

    name = fields.Char(u"Type de bordereau", readonly=True)
    transporter_id = fields.Many2one('tracking.transporter', u"Transporteur")
    code = fields.Char(u"Code Transporteur", readonly=True)
    is_relais = fields.Boolean(u"Point relais", readonly=True)
    used_from_customer = fields.Boolean(u"Utilisé pour les retours depuis le client")
    used_to_customer = fields.Boolean(u"Utilisé pour les envois vers le client")
    used_on_demand = fields.Boolean(u"Utilisé à la carte", compute='_compute_used_on_demand', store=True)
    output_printing_type_default_id = fields.Many2one('output.printing.type', u"Format d'impression par défaut")
    report_id = fields.Many2one('ir.actions.report.xml', u"Rapport utilisé pour générer le bordereau",
                                domain=[('model', '=', 'generate.tracking.labels.wizard')])

    @api.depends('used_from_customer', 'used_to_customer')
    def _compute_used_on_demand(self):
        for rec in self:
            rec.used_on_demand = rec.used_from_customer or rec.used_to_customer


class GenerateLabelOutputPrintingType(models.Model):
    _name = 'output.printing.type'

    name = fields.Char(u"Format de sortie", readonly=True)
    transporter_id = fields.Many2one('tracking.transporter', u"Transporteur")
    code = fields.Char(u"Code Transporteur", readonly=True)
    print_on_a4 = fields.Boolean(u"Imprimer sur A4")

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s, %s" % (rec.transporter_id.name, rec.name)))
        return res


class TransporterContentType(models.Model):
    _name = 'transporter.content.type'
    _description = u"Type de contenu du colis"

    name = fields.Char(u"Nom", readonly=True)
    transporter_id = fields.Many2one('tracking.transporter', u"Transporteur")
    code = fields.Char(u"Code", readonly=True)
    used_by_default = fields.Boolean(u"Utilisé par défaut pour ce transporteur")


class TrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    type_produit_expedition_ids = fields.One2many('type.produit.expedition', 'transporter_id', u"Produit transporteur")
    output_printing_type_ids = fields.One2many('output.printing.type', 'transporter_id', u"Format d'impression")
    transporter_content_type_ids = fields.One2many('transporter.content.type', 'transporter_id', u"Format d'impression")

    @api.multi
    def _get_default_content_type(self):
        self.ensure_one()
        return self.env['transporter.content.type'].search([
            ('transporter_id', '=', self.id), ('used_by_default', '=', True)
        ], limit=1)
