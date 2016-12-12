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

from openerp import models, api, fields, exceptions, _
import requests
from openerp.tools import ustr


class GenerateTrackingLabelsWizardColissimo(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    @api.multi
    def generate_label(self):
        result = super(GenerateTrackingLabelsWizardColissimo, self).generate_label()
        if self.transporter_id.name == 'Colissimo':
            company = self.env['res.users'].browse(self.env.uid).company_id
            contractNumber = self.env['ir.config_parameter'].\
                get_param('generate_tracking_labels_colissimo.login_colissimo', default='')
            password = self.env['ir.config_parameter'].\
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
            #TODO: veut-on faire du mailBoxPicking ?

            commercialName = company.name or ''
            orderNumber = ''

            # Destinataire
            companyName2 = company.name or ''
            lastName2 = company.name or ''
            firstName2 = company.name or ''
            line02 = ''
            line12 = ''
            line22 = company.street or ''
            line32 = company.street2 or ''
            countryCode2 = 'FR'
            city2 = company.city or ''
            zipCode2 = company.zip or ''
            phoneNumber2 = company.phone and company.phone.replace(' ', '').replace('-', '') or ''
            mobileNumber2 = ''
            doorCode12 = ''
            doorCode22 = ''
            email2 = company.email or ''
            intercom2 = ''
            language2 = 'FR'

    #TODO: returntype (si on veut aussi que l'étiquette soit envoyée à une certaine adresse mail),
    #TODO: pickuplocationid (identifiant du point de retrait), bloc custom (douane)


            first_part = (contractNumber, password, x, y, self.output_printing_type_id.code,
                          self.produit_expedition_id.code, depositDate, mailBoxPicking,
                          int(self.transportation_amount * 100), int(self.total_amount * 100), orderNumber,
                          commercialName, self.return_type_choice, self.weight, self.non_machinable, self.instructions,
                          self.ftd, self.sender_parcel_ref)

            customer_data = (self.company_name or '', self.last_name or '', self.first_name or '', self.line0 or '',
                             self.line1 or '', self.line2 or '', self.line3 or '', self.country_id.code or '',
                             self.city or '', self.zip or '', self.phone_number or '', self.mobile_number or '',
                             self.door_code1 or '', self.door_code2 or '', self.email or '', self.intercom or '',
                             self.language)

            second_part = (self.adressee_parcel_ref or '', self.code_bar_for_reference or '', self.service_info or '')

            our_data = (companyName2, lastName2, firstName2, line02, line12, line22, line32, countryCode2, city2, zipCode2,
                        phoneNumber2, mobileNumber2, doorCode12, doorCode22, email2, intercom2, language2)

            if self.direction == 'from_customer':
                parameters = first_part + customer_data + second_part + our_data
            else:
                parameters = first_part + our_data + second_part + customer_data

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
            </outputFormat>
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
                  <weight>%s</weight>
                  <nonMachinable>%s</nonMachinable>
                  <instructions>%s</instructions>
                  <ftd>%s</ftd>
               </parcel>
               <sender>
                  <senderParcelRef>%s</senderParcelRef>
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
            """ % (parameters)

            encoded_request = xml_post_parameter.encode('utf-8')
            headers = {"Content-Type": "text/xml; charset=UTF-8",
                       "Content-Length": len(encoded_request)}
            response = requests.post(url="https://ws.colissimo.fr/sls-ws/SlsServiceWS?wsdl",
                                     headers = headers,
                                     data = encoded_request,
                                     verify=False)
            tracking_number = False
            if len(response.content.split('<parcelNumber>')) > 1 and \
                    response.content.split('<parcelNumber>')[1].split('</parcelNumber>'):
                tracking_number = response.content.split('<parcelNumber>')[1].split('</parcelNumber>')[0]
            if tracking_number:
                outputfile = self.get_output_file(self.direction)
                response_string = response.content
                if len(response.content.split('<pdfUrl>')) == 2 and\
                    len(response.content.split('<pdfUrl>')[1].split('</pdfUrl>')) == 2:
                    url = response.content.split('<pdfUrl>')[1].split('</pdfUrl>')[0].replace('amp;', '')
                    file = requests.get(url)
                    outputfile = self.get_output_file(self.direction)
                    self.create_attachment(outputfile, self.direction, file=file.content)
                    return tracking_number, self.save_tracking_number, self.direction, url
                elif len(response_string.split('%PDF')) == 2 and response_string.split('%PDF')[1].split('%EOF'):
                    pdf_binary_string = '%PDF' + response_string.split('%PDF')[1].split('%EOF')[0] + '%EOF' + '\n'
                    self.create_attachment(outputfile, self.direction, pdf_binary_string=pdf_binary_string)
                    return tracking_number, self.save_tracking_number, self.direction, False
            if len(response.content.split('<messageContent>')) == 2 and\
                len(response.content.split('<messageContent>')[1].split('</messageContent>')) == 2:
                raise exceptions.except_orm(u"Erreur !", u'Colissimo : ' + ustr(response.content).
                                            split('<messageContent>')[1].split('</messageContent>')[0])
            raise exceptions.except_orm(u"Erreur !", u"Impossible de générer l'étiquette")
        return result
