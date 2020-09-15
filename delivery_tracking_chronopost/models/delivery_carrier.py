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

import requests
import zeep

from odoo import fields, models, api
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def chronopost_rate_shipment(self, order):
        return self.fixed_rate_shipment(order)

    @api.model
    def _chronopost_get_esd_value(self):
        return {
            'closingDateTime': '',
            'height': 0,
            'length': 0,
            'retrievalDateTime': '',
            'shipperBuildingFloor': '',
            'shipperCarriesCode': '',
            'shipperServiceDirection': '',
            'specificInstructions': '',
            'width': 0,
            'ltAImprimerParChronopost': 'N',
            'nombreDePassageMaximum': 1,
            'refEsdClient': '',
        }

    @api.model
    def _chronopost_get_header_value(self, picking):
        return {
            'accountNumber': picking.carrier_id.provider_id.api_account_number_chronopost,
            'idEmit': '',
            'identWebPro': '',
            'subAccount': '',
        }

    @api.model
    def _chronopost_get_shipper_value(self, picking):
        return {
            'shipperAdress1': self.env.user.company_id.partner_id.street or '',
            'shipperAdress2': self.env.user.company_id.partner_id.street2 or '',
            'shipperCity': self.env.user.company_id.partner_id.city or '',
            'shipperCivility': self.env.user.company_id.partner_id.title or 'M',
            'shipperContactName': '',
            'shipperCountry': self.env.user.company_id.country_id.code or '',
            'shipperCountryName': self.env.user.company_id.country_id.name.upper() or '',
            'shipperEmail': self.env.user.company_id.partner_id.email or '',
            'shipperMobilePhone': self.env.user.company_id.partner_id.mobile or '',
            'shipperName': self.env.user.company_id.partner_id.name or '',
            'shipperName2': '',
            'shipperPhone': self.env.user.company_id.partner_id.phone or '',
            'shipperPreAlert': picking.carrier_id.provider_id.api_pre_alert_chronopost or 0,
            'shipperZipCode': self.env.user.company_id.partner_id.zip or '',
        }

    @api.model
    def _chronopost_get_recipient_value(self, picking):
        return {
            'recipientAdress1': picking.partner_id.street or '',
            'recipientAdress2': picking.partner_id.street2 or '',
            'recipientCity': picking.partner_id.city or '',
            'recipientContactName': picking.partner_id.name or '',
            'recipientCountry': picking.partner_id.country_id.code or '',
            'recipientCountryName': picking.partner_id.country_id.name.upper() or '',
            'recipientEmail': picking.partner_id.email or '',
            'recipientMobilePhone': picking.partner_id.mobile or '',
            'recipientName': picking.partner_id.name or '',
            'recipientName2': '',
            'recipientPhone': picking.partner_id.phone or '',
            'recipientPreAlert': picking.carrier_id.provider_id.api_pre_alert_chronopost or 0,
            'recipientZipCode': picking.partner_id.zip or '',
        }

    @api.model
    def _chronopost_get_customer_value(self, picking):
        return {
            'customerAdress1': self.env.user.company_id.partner_id.street or '',
            'customerAdress2': self.env.user.company_id.partner_id.street2 or '',
            'customerCity': self.env.user.company_id.partner_id.city or '',
            'customerCivility': self.env.user.company_id.partner_id.title or 'M',
            'customerContactName': self.env.user.name or '',
            'customerCountry': self.env.user.company_id.country_id.code or '',
            'customerCountryName': self.env.user.company_id.country_id.name.upper() or '',
            'customerEmail': self.env.user.company_id.partner_id.email or '',
            'customerMobilePhone': self.env.user.company_id.partner_id.mobile or '',
            'customerName': self.env.user.company_id.partner_id.name or '',
            'customerName2': '',
            'customerPhone': self.env.user.company_id.partner_id.phone or '',
            'customerPreAlert': picking.carrier_id.provider_id.api_pre_alert_chronopost or 0,
            'customerZipCode': self.env.user.company_id.partner_id.zip or '',
            'printAsSender': '',
        }

    @api.model
    def _chronopost_get_ref_value(self):
        return {
            'customerSkybillNumber': '',
            'PCardTransactionNumber': '',
            'recipientRef': '',
            'shipperRef': '',
        }

    @api.model
    def _chronopost_get_skybill_value(self, picking, package):
        ship_date = fields.Datetime.now().isoformat()
        return {
            'bulkNumber': '',
            'codCurrency': '',
            'codValue': '',
            'content1': '',
            'content2': '',
            'content3': '',
            'content4': '',
            'content5': '',
            'customsCurrency': 'EUR',
            'customsValue': '',
            'evtCode': 'DC',
            'insuredCurrency': 'EUR',
            'insuredValue': '',
            'latitude': '',
            'longitude': '',
            'masterSkybillNumber': '',
            'objectType': 'MAR',
            'portCurrency': '',
            'portValue': '',
            'productCode': picking.carrier_id.carrier_code or '',
            'qualite': '',
            'service': 0,
            'shipDate': ship_date,
            'shipHour': ship_date and ship_date[11:13],
            'skybillRank': '',
            'source': '',
            'weight': package.shipping_weight / 1000,
            'weightUnit': 'KGM',
            'height': 0,
            'length': 0,
            'width': 0,
        }

    @api.model
    def _chronopost_get_skybill_params_value(self):
        return {
            'duplicata': '',
            'mode': 'PDF',
        }

    @api.model
    def _chronopost_get_scheduled_value(self):
        return {
            'appointmentValue': {
                'timeSlotEndDate': '',
                'timeSlotStartDate': '',
                'timeSlotTariffLevel': '',
            },
            'expirationDate': '',
            'sellByDate': '',
        }

    @api.model
    def _chronopost_get_letter(self, picking, package):
        return {
            'esdValue': self._chronopost_get_esd_value(),
            'headerValue': self._chronopost_get_header_value(picking),
            'shipperValue': self._chronopost_get_shipper_value(picking),
            'customerValue': self._chronopost_get_customer_value(picking),
            'recipientValue': self._chronopost_get_recipient_value(picking),
            'refValue': self._chronopost_get_ref_value(),
            'skybillValue': self._chronopost_get_skybill_value(picking, package),
            'skybillParamsValue': self._chronopost_get_skybill_params_value(),
            'password': picking.carrier_id.provider_id.api_password_chronopost,
            'modeRetour': '',
            'numberOfParcel': 1,
            'version': '',
            'multiParcel': '',
            'scheduledValue': self._chronopost_get_scheduled_value(),
        }

    @api.model
    def _chronopost_get_label(self, value, picking):
        url_ws = 'https://ws.chronopost.fr/shipping-cxf/ShippingServiceWS?wsdl'
        client = zeep.Client(url_ws)
        reponse = client.service.shippingMultiParcelWithReservation(**value['letter'])
        if reponse:
            if reponse.errorCode != 0:
                raise UserError("Erreur d'appel à Chronopost: %s.\n%s" % (reponse.errorCode, reponse.errorMessage))
            tracking_number = reponse.resultParcelValue[0]['skybillNumber']
            if tracking_number:
                url = 'https://www.chronopost.fr/shipping-cxf/getReservedSkybill?reservationNumber=' + tracking_number
                label = requests.get(url)
                return picking.save_tracking_number(tracking_number, label.content)

    def chronopost_send_shipping(self, pickings):
        all_values = []
        for picking in pickings:
            for package in picking.package_ids:
                if package.shipping_weight <= 0:
                    raise UserError("Le poid du colis est de 0")
                value_letter = self._chronopost_get_letter(picking, package)
                # on lance le webservice pour générer l'étiquette selon les paramètres
                genere = True
                if genere:
                    login = picking.carrier_id.provider_id.api_login_chronopost
                    password = picking.carrier_id.provider_id.api_password_chronopost
                    value_colis = {
                        'name': picking.partner_id.id,
                        'contract_number': login,
                        'password': password,
                        'output_format': "PDF_10x15_300dpi",
                        'letter': value_letter,
                        'date_envoi': picking.scheduled_date,
                        'bl': picking.id,
                    }
                    value_colis['label'] = self._chronopost_get_label(value_colis, picking)
                    all_values.append({
                        'exact_price': 0,
                        'tracking_number': value_colis['label'].name
                    })
        return all_values

    @api.model
    def chronopost_get_tracking_link(self, picking):
        tracking_number = self.env['delivery.carrier.tracking.number'].search([
            ('carrier_id', '=', picking.carrier_id.id)
        ], limit=1)
        return "https://www.chronopost.fr/tracking-no-cms/suivi-page?listeNumerosLT=%s" % tracking_number.name

    @api.model
    def chronopost_cancel_shipment(self, pickings):
        for picking in pickings:
            tracking_number = self.env['delivery.carrier.tracking.number'].search([
                ('carrier_id', '=', picking.carrier_id.id)
            ], limit=1)
            cancel_skybill = {
                'accountNumber': picking.carrier_id.provider_id.api_login_chronopost,
                'password': picking.carrier_id.provider_id.api_password_chronopost,
                'skybillNumber': tracking_number,
            }
            url_ws = 'https://ws.chronopost.fr/tracking-cxf/TrackingServiceWS?wsdl'
            client = zeep.Client(url_ws)
            client.service.cancelSkybill(**cancel_skybill)

    @api.model
    def chronopost_get_default_custom_package_code(self):
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        return picking.carrier_id.product_id.default_code
