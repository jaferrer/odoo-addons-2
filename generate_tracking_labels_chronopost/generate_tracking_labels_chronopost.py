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

import requests

from lxml import etree
from openerp import models, api, fields, tools
from openerp.exceptions import UserError
from openerp.tools import ustr


class GenerateTrackingLabelsWizardChronopost(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    client_pre_alert_chronopost = fields.Selection([('0', u"Pas de préalerte"),
                                                    ('11', u"Abonnement tracking expéditeur")],
                                                   string=u"Pré-alerte Chronopost pour le client", default='0',
                                                   required=True)
    mode_retour = fields.Selection([('1', u"Oui"), ('2', u"Non")],
                                   string=u"Envoyer l'étiquette par mail à l'expéditeur", default='2', required=True)
    service = fields.Selection([('0', u"Normal"),
                                ('1', u"Lundi"),
                                ('2', u"Mardi"),
                                ('3', u"Mercredi"),
                                ('4', u"Jeudi"),
                                ('5', u"Vendredi"),
                                ('6', u"Samedi")], string=u"Jour de la livraison", default='0', required=True)

    @api.model
    def convert_title_chronopost(self, title):
        shipper_civility = ''
        if title == self.env.ref('base.res_partner_title_madam'):
            shipper_civility = 'E'
        elif self.env.ref('base.res_partner_title_miss'):
            shipper_civility = 'L'
        elif self.env.ref('base.res_partner_title_sir'):
            shipper_civility = 'M'
        elif self.env.ref('base.res_partner_title_mister'):
            shipper_civility = 'M'
        return shipper_civility

    @api.multi
    def generate_label(self):
        result = super(GenerateTrackingLabelsWizardChronopost, self).generate_label()
        if self.transporter_id == self.env.ref('base_delivery_tracking_chronopost.transporter_chronopost'):
            account_number = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_chronopost.login_chronopost', default='')
            password = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_chronopost.password_chronopost', default='')
            company_pre_alert_chronopost = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_chronopost.pre_alert_chronopost', default='')
            if not account_number or not password:
                raise UserError(u"Veuillez remplir la configuration Chronopost")

            # evc_code : valeur unique
            packages_data = self.get_packages_data()

            # TODO: ajouter champs
            closing_date_time = ''
            retrieval_date_time = ''
            shipper_building_floor = ''
            shipper_carries_code = ''
            shipper_service_direction = ''
            specific_instructions = ''
            height = 0
            length = 0
            width = 0
            it_a_imprimer_par_chronopost = 'N'
            nombre_de_passage_maximum = 1
            ref_eds_client = ''

            idEmit = ''
            sub_account = ''
            header_values = (account_number or '', idEmit or '', sub_account or '')

            company_name_1 = self.partner_orig_id.company_id.name
            company_civility = self.convert_title_chronopost(self.partner_orig_id.company_id.partner_id.title)
            company_name_2 = self.env.user.name
            shipper_name = self.env.user.name
            company_adress_1 = self.partner_orig_id.street or ''
            company_adress_2 = self.partner_orig_id.street2 or ''
            company_zip = self.partner_orig_id.zip
            company_city = self.partner_orig_id.city
            company_country = self.partner_orig_id.country_id.code
            company_country_name = self.partner_orig_id.country_id.name.upper()
            company_phone = self.partner_orig_id.phone
            company_mobile_phone = self.partner_orig_id.mobile
            company_email = self.partner_orig_id.email
            company_description = (company_name_1 or '', company_civility or 'M', company_name_2 or '',
                                   shipper_name or '', company_adress_1 or '',)
            company_adress_data = (company_zip or '', company_city or '', company_country or '',
                                   company_country_name or '', company_phone or '', company_mobile_phone or '',
                                   company_email or '', company_pre_alert_chronopost or '0')

            customer_name_1 = self.company_name
            customer_civility = self.convert_title_chronopost(self.partner_id.title)
            customer_name_2 = ''
            shipper_name_2 = ''
            customer_adress_1 = self.line2 or ''
            customer_adress_2 = self.line3 or ''
            customer_zip = self.zip
            customer_city = self.city
            customer_country = self.country_id.code
            customer_country_name = self.country_id.name.upper()
            customer_phone = self.phone_number
            customer_mobile_phone = self.mobile_number
            customer_email = self.email
            customer_pre_alert = self.client_pre_alert_chronopost or '0'
            customer_description = (customer_name_1,customer_civility or 'M', customer_name_2 or '',
                                    shipper_name_2 or '', customer_adress_1 or '',)
            customer_adress_data = (customer_zip or '', customer_city or '', customer_country or '',
                                    customer_country_name or '', customer_phone or '', customer_mobile_phone or '',
                                    customer_email or '', customer_pre_alert or '')

            # print_as_sender = self.direction == 'to_customer' and 'N' or 'Y'
            print_as_sender = ''

            # TODO: calculer
            recipient_ref = ''
            customer_sky_bill_number = ''
            ref_value = (self.sender_parcel_ref or '', recipient_ref or '', customer_sky_bill_number or '')

            number_of_parcel = len(packages_data)
            multi_parcel = number_of_parcel == 1 and 'N' or 'Y'
            final_data = (password or '', self.mode_retour or '', number_of_parcel, multi_parcel or '')

            eds_values = (closing_date_time or '', retrieval_date_time or '', shipper_building_floor or '',
                          shipper_carries_code or '', shipper_service_direction or '', specific_instructions or '',
                          height, length, width, it_a_imprimer_par_chronopost or '',
                          nombre_de_passage_maximum, ref_eds_client or '')

            shipper_description = self.direction == 'to_customer' and company_description or customer_description
            shipper_adress_2 = self.direction == 'to_customer' and company_adress_2 or customer_adress_2
            shipper_adress_data = self.direction == 'to_customer' and company_adress_data or customer_adress_data

            recipient_description = self.direction == 'from_customer' and company_description or customer_description
            recipient_adress_2 = self.direction == 'from_customer' and company_adress_2 or customer_adress_2
            recipient_adress_data = self.direction == 'from_customer' and company_adress_data or customer_adress_data

            xml_post_parameter = u"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cxf="http://cxf.shipping.soap.chronopost.fr/">
   <soapenv:Header/>
   <soapenv:Body>
      <cxf:shippingMultiParcelWithReservation>
         <esdValue>
            <closingDateTime>%s</closingDateTime>
            <retrievalDateTime>%s</retrievalDateTime>
            <shipperBuildingFloor>%s</shipperBuildingFloor>
            <shipperCarriesCode>%s</shipperCarriesCode>
            <shipperServiceDirection>%s</shipperServiceDirection>
            <specificInstructions>%s</specificInstructions>
            <height>%s</height>
            <length>%s</length>
            <width>%s</width>
            <ltAImprimerParChronopost>%s</ltAImprimerParChronopost>
            <nombreDePassageMaximum>%s</nombreDePassageMaximum>
            <refEsdClient>%s</refEsdClient>
         </esdValue>""" % eds_values
            xml_post_parameter += u"""
         <headerValue>
            <accountNumber>%s</accountNumber>
            <idEmit>%s</idEmit>
            <identWebPro></identWebPro>
            <subAccount>%s</subAccount>
         </headerValue>""" % header_values
            xml_post_parameter += u"""
         <shipperValue>
	        <shipperName>%s</shipperName>
	        <shipperCivility>%s</shipperCivility>
            <shipperContactName>%s</shipperContactName>
            <shipperName2>%s</shipperName2>
	        <shipperAdress1>%s</shipperAdress1>""" % shipper_description
            if company_adress_2:
                xml_post_parameter += u"""
            <shipperAdress2>%s</shipperAdress2>""" % shipper_adress_2
            xml_post_parameter += u"""
            <shipperZipCode>%s</shipperZipCode>
            <shipperCity>%s</shipperCity>
            <shipperCountry>%s</shipperCountry>
            <shipperCountryName>%s</shipperCountryName>
            <shipperPhone>%s</shipperPhone>
            <shipperMobilePhone>%s</shipperMobilePhone>
            <shipperEmail>%s</shipperEmail>
            <shipperPreAlert>%s</shipperPreAlert>
         </shipperValue>""" % shipper_adress_data
            xml_post_parameter += u"""
         <customerValue>
	        <customerName>%s</customerName>
	        <customerCivility>%s</customerCivility>
            <customerContactName>%s</customerContactName>
            <customerName2>%s</customerName2>
	        <customerAdress1>%s</customerAdress1>""" % company_description
            if company_adress_2:
                xml_post_parameter += u"""
            <customerAdress2>%s</customerAdress2>""" % company_adress_2
            xml_post_parameter += u"""
            <customerZipCode>%s</customerZipCode>
            <customerCity>%s</customerCity>
            <customerCountry>%s</customerCountry>
            <customerCountryName>%s</customerCountryName>
            <customerPhone>%s</customerPhone>
            <customerMobilePhone>%s</customerMobilePhone>
            <customerEmail>%s</customerEmail>
            <customerPreAlert>%s</customerPreAlert>""" % company_adress_data
            xml_post_parameter += u"""
            <printAsSender>%s</printAsSender>
         </customerValue>""" % print_as_sender
            xml_post_parameter += u"""
         <recipientValue>
            <recipientName>%s</recipientName>
            <recipientName2>%s</recipientName2>
	        <recipientCivility>%s</recipientCivility>
            <recipientContactName>%s</recipientContactName>
            <recipientAdress1>%s</recipientAdress1>""" % recipient_description
            if customer_adress_2:
                xml_post_parameter += u"""
            <recipientAdress2>%s</recipientAdress2>""" % recipient_adress_2
            xml_post_parameter += u"""
            <recipientZipCode>%s</recipientZipCode>
            <recipientCity>%s</recipientCity>
            <recipientCountry>%s</recipientCountry>
            <recipientCountryName>%s</recipientCountryName>
            <recipientPhone>%s</recipientPhone>
            <recipientMobilePhone>%s</recipientMobilePhone>
            <recipientEmail>%s</recipientEmail>
            <recipientPreAlert>%s</recipientPreAlert>
         </recipientValue>""" % recipient_adress_data
            xml_post_parameter += u"""
         <refValue>
            <customerSkybillNumber>%s</customerSkybillNumber>
            <PCardTransactionNumber></PCardTransactionNumber>
            <recipientRef>%s</recipientRef>
            <shipperRef>%s</shipperRef>
         </refValue>""" % ref_value
            for pack_data in packages_data:
                # evt_code : valeur fixe
                evt_code = 'DC'
                ship_date = fields.Datetime.now().replace(' ', 'T')
                ship_hour = ship_date and ship_date[11:13]
                service = self.service
                object_type = self.content_type_id.code
                sky_bill_value = (pack_data['cod_value'] or '',  pack_data['amount_total'] or '', evt_code or '',
                                  pack_data['amount_total'] or '', object_type or '',
                                  self.produit_expedition_id.code or '', service or '', ship_date, ship_hour or '',
                                  pack_data['weight'], pack_data['height'], pack_data['lenght'], pack_data['width'])
                xml_post_parameter += u"""
         <skybillValue>
            <bulkNumber></bulkNumber>
            <codCurrency>EUR</codCurrency>
            <codValue>%s</codValue>
            <content1></content1>
            <content2></content2>
            <content3></content3>
            <content4></content4>
            <content5></content5>
            <customsCurrency>EUR</customsCurrency>
            <customsValue>%s</customsValue>
            <evtCode>%s</evtCode>
            <insuredCurrency>EUR</insuredCurrency>
            <insuredValue>%s</insuredValue>
            <objectType>%s</objectType>
            <portCurrency></portCurrency>
            <portValue></portValue>
            <productCode>%s</productCode>
            <service>%s</service>
            <shipDate>%s</shipDate>
            <shipHour>%s</shipHour>
            <skybillRank></skybillRank>
            <weight>%s</weight>
            <weightUnit>KGM</weightUnit>
            <height>%s</height>
            <length>%s</length>
            <width>%s</width>
         </skybillValue>""" % sky_bill_value
            xml_post_parameter += u"""
         <skybillParamsValue>
            <mode>%s</mode>
         </skybillParamsValue>""" % self.output_printing_type_id.code or ''
            xml_post_parameter += u"""
         <password>%s</password>
         <modeRetour>%s</modeRetour>
         <numberOfParcel>%s</numberOfParcel>
         <multiParcel>%s</multiParcel>""" % final_data
            xml_post_parameter += u"""
      </cxf:shippingMultiParcelWithReservation>
   </soapenv:Body>
</soapenv:Envelope>"""

            encoded_request = tools.ustr(xml_post_parameter).encode('utf-8')
            headers = {"Content-Type": "text/xml; charset=UTF-8",
                       "Content-Length": len(encoded_request)}
            response = requests.post(url="https://www.chronopost.fr/shipping-cxf/ShippingServiceWS",
                                     headers=headers,
                                     data=encoded_request,
                                     verify=False)

            reservation_number = False
            if len(response.content.split('<reservationNumber>')) > 1 and \
                    response.content.split('<reservationNumber>')[1].split('</reservationNumber>'):
                reservation_number = response.content.split('<reservationNumber>')[1].split('</reservationNumber>')[0]
            if reservation_number:
                url = 'https://www.chronopost.fr/shipping-cxf/getReservedSkybill?reservationNumber=' + reservation_number
                label = requests.get(url)
                if len(label.content.split('%PDF')) == 2 and label.content.split('%PDF')[1].split('%EOF'):
                    pdf_binary_string = '%PDF' + label.content.split('%PDF')[1].split('%EOF')[0] + '%EOF' + '\n'
                    self.create_attachment([pdf_binary_string])
                    root = etree.XML(response.content)
                    tracking_numbers = [x.text for x in root.iterfind(".//resultParcelValue/skybillNumber")]
                    return tracking_numbers
            if response.content == '<html><body>No service was found.</body></html>':
                raise UserError(u"Service non trouvé")
            if len(response.content.split('<faultstring>')) > 1 and \
                            len(response.content.split('<faultstring>')[1].split('</faultstring>')) > 1:
                msg = ustr(response.content).split('<faultstring>')[1].split('</faultstring>')[0]
                if msg:
                    raise UserError(msg)
            if len(response.content.split('<errorMessage>')) == 2 and \
                            len(response.content.split('<errorMessage>')[1].split('</errorMessage>')) == 2:
                msg = ustr(response.content).split('<errorMessage>')[1].split('</errorMessage>')[0]
                if msg:
                    raise UserError(msg)
            raise UserError(u"Impossible de générer l'étiquette")
        return result
