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

from openerp import models, api, fields, exceptions
from openerp.exceptions import UserError
from openerp.tools import ustr


class GenerateTrackingLabelsWizardColissimo(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    @api.multi
    def generate_label(self):
        result = super(GenerateTrackingLabelsWizardColissimo, self).generate_label()
        if self.transporter_id == self.env.ref('base_delivery_tracking_colissimo.transporter_colissimo'):
            contractNumber = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_colissimo.login_colissimo', default='')
            password = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_colissimo.password_colissimo', default='')
            if self.code_bar_for_reference == 'true' and self.produit_expedition_id.code != 'CORE':
                raise exceptions.except_orm('Erreur !', "Impossible d'afficher le code barre retour pour un autre "
                                                        "produit que Colissimo retour")
            if self.service_info and self.produit_expedition_id.code != 'CORE':
                raise exceptions.except_orm('Erreur !', "Impossible de définir un nom de service en retour pour un "
                                                        "autre produit que Colissimo retour")
            depositDate = fields.Date.today()
            x = 0
            y = 0
            mailBoxPicking = 'false'
            # TODO: veut-on faire du mailBoxPicking ?

            packages_data = self.get_packages_data()

            tracking_numbers = []
            list_files = []

            commercialName = self.partner_orig_id.company_id.name or ''
            orderNumber = self.get_order_number()

            # Destinataire
            companyName2 = self.partner_orig_id.company_id.name or ''
            lastName2 = self.partner_orig_id.company_id.name or ''
            firstName2 = self.partner_orig_id.company_id.name or ''
            line02 = ''
            line12 = ''
            line22 = self.partner_orig_id.street or ''
            line32 = self.partner_orig_id.street2 or ''
            countryCode2 = self.partner_orig_id.country_id.code or ''
            city2 = self.partner_orig_id.city or ''
            zipCode2 = self.partner_orig_id.zip or ''
            phoneNumber2 = self.partner_orig_id.phone and \
                           self.partner_orig_id.phone.replace(' ', '').replace('-', '') or ''
            mobileNumber2 = ''
            doorCode12 = ''
            doorCode22 = ''
            email2 = self.partner_orig_id.email or ''
            intercom2 = ''
            language2 = 'FR'

            # TODO: returntype (si on veut aussi que l'étiquette soit envoyée à une certaine adresse mail),
            # TODO: pickuplocationid (identifiant du point de retrait), bloc custom (douane)

            for package_data in packages_data:
                pack_data = (self.produit_expedition_id.code, depositDate, mailBoxPicking,
                             int(package_data['amount_untaxed'] * 100), int(package_data['amount_total'] * 100),
                             orderNumber, commercialName, self.return_type_choice, package_data['amount_total'],
                             package_data['weight'], self.non_machinable,
                             bool(package_data['cod_value']) and 1 or 0, package_data['cod_value'] * 100,
                             self.instructions, self.ftd)

                customer_spec = {
                    'line0': self.line0 or '',
                    'line1': self.line1 or '',
                    'line2': self.line2 or '',
                    'line3': self.line3 or ''
                }
                if self.country_id.code == 'BE':
                    customer_spec = {
                        'line0': self.line3 and (self.line2 or '') or '',
                        'line1': '',
                        'line2': self.line3 and (self.line3 or '') or (self.line2 or ''),
                        'line3': ''
                    }


                customer_data = (self.company_name or '', self.last_name or '', self.first_name or '', customer_spec['line0'],
                                 customer_spec['line1'], customer_spec['line2'], customer_spec['line3'], self.country_id.code or '',
                                 self.city or '', self.zip or '', self.phone_number or '', self.mobile_number or '',
                                 self.door_code1 or '', self.door_code2 or '', self.email or '', self.intercom or '',
                                 self.language)

                data_for_adressee = (self.adressee_parcel_ref or '', self.code_bar_for_reference or '',
                                     self.service_info or '')

                our_data = (companyName2, lastName2, firstName2, line02, line12, line22, line32, countryCode2, city2,
                            zipCode2, phoneNumber2, mobileNumber2, doorCode12, doorCode22, email2, intercom2, language2)

                xml_post_parameter = u"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sls="http://sls.ws.coliposte.fr">
    <soapenv:Header/>
        <soapenv:Body>
          <sls:generateLabel>
             <generateLabelRequest>
                <contractNumber>%s</contractNumber>
                <password>%s</password>
                <outputFormat>
                   <x>%s</x>
                   <y>%s</y>
                   <outputPrintingType>%s</outputPrintingType>
                </outputFormat>""" % (contractNumber, password, x, y, self.output_printing_type_id.code)
                xml_post_parameter += u"""
                <letter>
                   <service>
                      <productCode>%s</productCode>
                      <depositDate>%s</depositDate>
                      <mailBoxPicking>%s</mailBoxPicking>
                      <transportationAmount>%s</transportationAmount>
                      <totalAmount>%s</totalAmount>
                      <orderNumber>%s</orderNumber>
                      <commercialName>%s</commercialName>
                      <returnTypeChoice>%s</returnTypeChoice>
                   </service>
                   <parcel>
                      <insuranceValue>%s</insuranceValue>
                      <weight>%s</weight>
                      <nonMachinable>%s</nonMachinable>
                      <COD>%s</COD>
                      <CODAmount>%s</CODAmount>
                      <instructions>%s</instructions>
                      <ftd>%s</ftd>
                   </parcel>""" % pack_data
                if package_data.get('custom_declaration'):
                    xml_post_parameter += u"""
                       <customsDeclarations>
                           <includeCustomsDeclarations>1</includeCustomsDeclarations>
                              <contents>"""
                    for custom_declaration in package_data['custom_declaration']:
                        custom_data = (custom_declaration['description'],
                                       int(custom_declaration['quantity']),
                                       custom_declaration['weight'],
                                       custom_declaration['value'],
                                       custom_declaration['hs_code'],
                                       custom_declaration['country_code'])
                        xml_post_parameter += u"""
                                <article>
                                    <description>%s</description>
                                    <quantity>%s</quantity>
                                    <weight>%s</weight>
                                    <value>%s</value>
                                    <hsCode>%s</hsCode>
                                    <originCountry>%s</originCountry>
                                </article>""" % custom_data
                    xml_post_parameter += u"""
                                <category>
                                    <value>%s</value>
                                </category>
                            </contents>
                            <importersReference>%s</importersReference>
                            <importersContact>%s</importersContact>
                            <officeOrigin>%s</officeOrigin>
                       </customsDeclarations>""" % (package_data['category'],
                                                    package_data['importers_reference'],
                                                    package_data['importers_contact'],
                                                    package_data['office_origin'])
                xml_post_parameter += u"""
                    <sender>
                      <senderParcelRef>%s</senderParcelRef>""" % self.sender_parcel_ref
                xml_post_parameter += u"""
                      <address>
                         <companyName>%s</companyName>
                         <lastName>%s</lastName>
                         <firstName>%s</firstName>
                         <line0>%s</line0>
                         <line1>%s</line1>
                         <line2>%s</line2>
                         <line3>%s</line3>
                         <countryCode>%s</countryCode>
                         <city>%s</city>
                         <zipCode>%s</zipCode>
                         <phoneNumber>%s</phoneNumber>
                         <mobileNumber>%s</mobileNumber>
                         <doorCode1>%s</doorCode1>
                         <doorCode2>%s</doorCode2>
                         <email>%s</email>
                         <intercom>%s</intercom>
                         <language>%s</language>
                      </address>
                   </sender>
                   <addressee>
                      <addresseeParcelRef>%s</addresseeParcelRef>
                      <codeBarForReference>%s</codeBarForReference>
                      <serviceInfo>%s</serviceInfo>
                      <address>
                         <companyName>%s</companyName>
                         <lastName>%s</lastName>
                         <firstName>%s</firstName>
                         <line0>%s</line0>
                         <line1>%s</line1>
                         <line2>%s</line2>
                         <line3>%s</line3>
                         <countryCode>%s</countryCode>
                         <city>%s</city>
                         <zipCode>%s</zipCode>
                         <phoneNumber>%s</phoneNumber>
                         <mobileNumber>%s</mobileNumber>
                         <doorCode1>%s</doorCode1>
                         <doorCode2>%s</doorCode2>
                         <email>%s</email>
                         <intercom>%s</intercom>
                         <language>%s</language>
                      </address>
                   </addressee>
                </letter>
             </generateLabelRequest>
          </sls:generateLabel>
        </soapenv:Body>
    </soapenv:Envelope>
                """ % (self.direction == 'from_customer' and customer_data + data_for_adressee + our_data or
                       our_data + data_for_adressee + customer_data)

                encoded_request = xml_post_parameter.encode('utf-8')
                headers = {"Content-Type": "text/xml; charset=UTF-8",
                           "Content-Length": len(encoded_request)}
                response = requests.post(url="https://ws.colissimo.fr/sls-ws/SlsServiceWS?wsdl",
                                         headers=headers,
                                         data=encoded_request,
                                         verify=False)
                tracking_number = False
                if len(response.content.split('<parcelNumber>')) > 1 and \
                        response.content.split('<parcelNumber>')[1].split('</parcelNumber>'):
                    tracking_number = response.content.split('<parcelNumber>')[1].split('</parcelNumber>')[0]
                if tracking_number:
                    tracking_numbers += [tracking_number]
                    response_string = response.content
                    if len(response.content.split('<pdfUrl>')) == 2 and \
                                    len(response.content.split('<pdfUrl>')[1].split('</pdfUrl>')) == 2:
                        url = response.content.split('<pdfUrl>')[1].split('</pdfUrl>')[0].replace('amp;', '')
                        file = requests.get(url)
                        list_files += [file.content]

                    elif len(response_string.split('%PDF')) == 2 and response_string.split('%PDF')[1].split('%EOF'):
                        pdf_binary_string = '%PDF' + response_string.split('%PDF')[1].split('%EOF')[0] + '%EOF' + '\n'
                        list_files += [pdf_binary_string]
                    continue
                if len(response.content.split('<messageContent>')) == 2 and \
                                len(response.content.split('<messageContent>')[1].split('</messageContent>')) == 2:
                    raise UserError(u'Colissimo : ' + ustr(response.content).
                                    split('<messageContent>')[1].split('</messageContent>')[0])
                if len(response.content.split('<faultstring>')) == 2 and \
                                len(response.content.split('<faultstring>')[1].split('</faultstring>')) == 2:
                    raise UserError(u'Colissimo : ' + ustr(response.content).
                                    split('<faultstring>')[1].split('</faultstring>')[0])
                raise UserError(u"Impossible de générer l'étiquette")

            self.create_attachment(list_files=list_files)
            return tracking_numbers
        return result
