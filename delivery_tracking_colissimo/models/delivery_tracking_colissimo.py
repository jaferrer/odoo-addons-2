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
import base64
import logging

from odoo import models, fields, api
from odoo.modules.module import get_module_resource
from suds.client import Client
from suds.plugin import MessagePlugin

_logger = logging.getLogger(__name__)


class MyPlugin(MessagePlugin):

    def __init__(self, *args, **kwargs):
        self.binary = False

    @api.model
    def marshalled(self, context):
        # on modifie la structure du fichier car elle est mal générée (deux fois generatelabel)
        envelope = context.envelope
        generate_label_request = envelope.getChild('Body').getChild('generateLabel').getChild(
            'generateLabelRequest').detachChildren()
        envelope.getChild('Body').getChild('generateLabel').detachChildren()
        envelope.getChild('Body').getChild('generateLabel').append(generate_label_request)

    @api.model
    def received(self, context):
        reply = context.reply

        debut_envelope = reply.find(b'<soap:Envelope')
        fin_envelope = reply.find(b'</soap:Envelope>')

        debut_label = reply.find(b'<label>')
        fin_label = reply.find(b'</label>')

        envelope = reply[debut_envelope:debut_label] + reply[fin_label + 8:fin_envelope + 16]

        # on met dans binary les données binaires
        debut_binary = reply.find(b'%PDF', fin_envelope)
        fin_binary = reply.find(b"--uuid:", debut_binary)

        binary = reply[debut_binary:fin_binary]

        self.binary = binary

        context.reply = envelope


class DeliveryCarrierColissimo(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('colissimo', "Colissimo")])
    api_login_colissimo = fields.Char("Login Colissimo", related='company_id.api_login_colissimo')
    api_password_colissimo = fields.Char("Password Colissimo", related='company_id.api_password_colissimo')

    @api.multi
    def _compute_image(self):
        super(DeliveryCarrierColissimo, self)._compute_image()
        for rec in self:
            if rec.delivery_type == 'colissimo':
                img_path = get_module_resource('delivery_tracking_colissimo', 'static/img', 'colissimo_logo.png')
                with open(img_path, 'rb') as file:
                    image = file.read()
                rec.image = base64.b64encode(image)

    @api.model
    def colissimo_rate_shipment(self, order):
        return self.fixed_rate_shipment(order)

    @api.model
    def _get_service(self, picking):
        return {
            'name': picking.carrier_id.product_id.default_code,
            'deposit_date': picking.scheduled_date,
            'mail_box_picking': False,
            'mail_box_picking_date': False,
            'transportation_amount': False,
            'total_amount': False,
            'order_number': picking.name,
            'name_commercial': self.env.user.name,
            'return_type_choice': False,
        }

    @api.model
    def _get_parcel(self, package):
        return {
            'name': package.name,
            'insurance_value': 0,
            'recommendation_level': False,
            'weight': package.shipping_weight / 1000,
            'non_machinable': False,
            'cod': False,
            'cod_amount': 0.0,
            'return_receipt': False,
            'instructions': "",
            'pickup_location_id': False,
            'ftd': False
        }

    @api.model
    def _get_sender(self):
        return {
            'name': self.env.user.company_id.partner_id.name,
            'address': self.env.user.company_id.partner_id.id,
        }

    @api.model
    def _get_addressee(self, picking):
        return {
            'name': picking.partner_id.name,
            'code_bar_for_reference': False,
            'service_info': self.env.user.company_id.name,
            'address': picking.partner_id.id,
        }

    @api.model
    def _get_letter(self, picking, package):
        value_letter = {
            'name': self._get_service(picking),
            'parcel': self._get_parcel(package),
            'sender': self._get_sender(),
            'addressee': self._get_addressee(picking),
            'customs_declarations': False,
        }

        return value_letter

    @api.model
    def odoo2laposte(self, value, client):

        contract_number = value['contract_number']
        password = value['password']

        generate_label = client.factory.create('generateLabel')

        generate_label_request = generate_label.generateLabelRequest

        output_format = generate_label_request.outputFormat
        letter = generate_label_request.letter
        service = letter.service
        parcel = letter.parcel
        sender = letter.sender
        sender_address = sender.address
        addressee = letter.addressee
        addressee_address = addressee.address

        ltr = value['letter']

        output_format.outputPrintingType = value['output_format']

        service.productCode = ltr['name']['name']
        service.depositDate = ltr['name']['deposit_date']
        service.orderNumber = ltr['name']['order_number']
        service.commercialName = ltr['name']['name_commercial']

        # parcel.weight = L.parcel.weight
        parcel.weight = ltr['parcel']['weight']

        sender_address.companyName = ltr['sender']['address'].company_id.name
        sender_address.line2 = ltr['sender']['address'].street
        sender_address.line3 = (ltr['sender']['address'].street2 or '') + "-" + (ltr['sender']['address'].street3 or '')
        sender_address.countryCode = 'FR'
        sender_address.city = ltr['sender']['address'].city
        sender_address.zipCode = ltr['sender']['address'].zip
        sender_address.email = ltr['sender']['address'].email or ''
        sender_address.phoneNumber = ltr['sender']['address'].phone or ''

        sender.senderParcelRef = ltr['sender'].name
        sender.address = sender_address

        # addressee_address.companyName = L.addressee.address.company_id.name
        addressee_address.companyName = ""
        addressee_address.lastName = ltr['addressee']['address'].street or ''
        addressee_address.firstName = "M"

        addressee_address.line2 = ltr['addressee']['address'].street2 or ''
        addressee_address.line3 = ltr['addressee']['address'].street3 or ''
        addressee_address.countryCode = 'FR'
        addressee_address.city = ltr['addressee']['address'].city
        addressee_address.zipCode = ltr['addressee']['address'].zip
        addressee_address.email = ltr['addressee']['address'].email or ''
        addressee_address.phoneNumber = ltr['addressee']['address'].phone or ''

        addressee.address = addressee_address

        letter.service = service
        letter.parcel = parcel
        letter.sender = sender
        letter.addressee = addressee

        generate_label_request.contractNumber = contract_number
        generate_label_request.password = password

        return generate_label

    @api.model
    def _get_label(self, value_colis, picking):
        url_ws = "https://ws.colissimo.fr/sls-ws/SlsServiceWS?wsdl"
        my_plugin = MyPlugin()
        client = Client(url_ws, plugins=[my_plugin])

        generate_label = self.odoo2laposte(value_colis, client)

        reponse = client.service.generateLabel(generate_label)

        if reponse:
            tracking_number = self.env['delivery.carrier.tracking.number'].create({
                'name': str(reponse.labelResponse.parcelNumber),
                'carrier_id': picking.carrier_id.id
            })
            label_name = "Colis %s" % reponse.labelResponse.parcelNumber
            self.env['ir.attachment'].create({
                'name': label_name,
                'datas': my_plugin.binary,
                'datas_fname': label_name,
                'type': 'binary',
                'res_model': 'delivery.carrier.tracking.number',
                'res_id': tracking_number.id,
            })
            return tracking_number
        return False

    @api.model
    def colissimo_send_shipping(self, pickings):
        all_values = []
        for picking in pickings:
            for package in picking.package_ids:

                if package.shipping_weight <= 0:
                    return False

                value_letter = self._get_letter(picking, package)

                # on lance le webservice pour générer l'étiquette selon les paramètres
                genere = True
                if genere:
                    login = picking.carrier_id.api_login_colissimo
                    password = picking.carrier_id.api_password_colissimo
                    value_colis = {
                        'name': picking.partner_id.id,
                        'contract_number': login,
                        'password': password,
                        'output_format': "PDF_10x15_300dpi",
                        'letter': value_letter,
                        'date_envoi': picking.scheduled_date,
                        'bl': picking.id,
                    }

                    value_colis['label'] = self._get_label(value_colis, picking)
                    all_values.append({
                        'exact_price': 0,
                        'tracking_number': value_colis['label'].name
                    })

        return all_values

    @api.model
    def colissimo_get_tracking_link(self, picking):
        """
        S'il y en a plusieurs, on ne retourne que le premier.
        """
        tracking_number = self.env['delivery.carrier.tracking.number'].search([
            ('carrier_id', '=', picking.carrier_id.id)
        ], limit=1)
        return "https://www.laposte.fr/outils/suivre-vos-envois?code=[%s]" % (tracking_number)

    @api.model
    def colissimo_cancel_shipment(self, pickings):
        """
        Non fournit par l'API colissimo.
        """
        return self.env['stock.picking']

    @api.model
    def colissimo_get_default_custom_package_code(self):
        """
        On retourne le code produit du Produit du Transporteur.
        """
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        return picking.carrier_id.product_id.default_code


class ResCompanyColissmi(models.Model):
    _inherit = 'res.company'

    api_login_colissimo = fields.Char("Login Colissimo")
    api_password_colissimo = fields.Char("Password Colissimo")
