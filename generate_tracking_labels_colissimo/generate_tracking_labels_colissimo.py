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
from urllib2 import urlopen
import requests


class GenerateTrackingLabelsWizard(models.TransientModel):
    _name = 'generate.tracking.labels.wizard'

    direction = fields.Selection([('to_customer', "Va vers le client"), ('from_customer', "Vient du client")],
                                 required=True)
    type = fields.Selection([('france', "France (ou OM)"), ('alien', "Etranger")], string=u"Type d'envoi",
                            required=True, default='france')
    save_tracking_number = fields.Boolean(string=u"Enregistrer le numéro de suivi pour ce cas", default=True)
    companyName = fields.Char(string=u"Raison sociale", required=True)
    lastName = fields.Char(string=u"Nom", required=True)
    firstName = fields.Char(string=u"Prénom", required=True)
    line0 = fields.Char(string=u"Etage, couloir, escalier, appartement")
    line1 = fields.Char(string=u"Entrée, bâtiment, immeuble, résidence")
    line2 = fields.Char(string=u"Numéro et libellé de voie. ", required=True)
    line3 = fields.Char(string=u"Lieu dit ou autre mention")
    countryCode = fields.Char(string=u"Code pays", default='FR', required=True, help=u"Code ISO du pays sur 2 lettres")
    city = fields.Char(string=u"Ville", required=True)
    zipCode = fields.Char(string=u"Code postal", required=True)
    phoneNumber = fields.Char(string=u"Tél")
    mobileNumber = fields.Char(string=u"Mobile")
    doorCode1 = fields.Char(string=u"Code porte 1")
    doorCode2 = fields.Char(string=u"Code porte 2")
    email = fields.Char(string=u"Email", required=True)
    intercom = fields.Char(string=u"Interphone")
    language = fields.Char(string=u"Langue", default='FR', required=True)
    adresseeParcelRef = fields.Char(string=u"Référence colis pour destinataire")
    codeBarForReference = fields.Selection([('false', 'Non'), ('true', 'Oui')], string=u"Afficher code barre",
                                           default='false', help=u"Pour les colissimo retours uniquement")
    serviceInfo = fields.Char(string=u"Nom du service de réception retour",
                              help=u"Pour les colissimo retours uniquement")
    instructions = fields.Char(string=u"Motif du retour")
    weight = fields.Float(string=u"Poids du colis", required=True)
    outputPrintingType = fields.Selection([('PDF_10x15_300dpi', "10X15 300 DPI"),
                                           ('PDF_A4_300dpi', "A4 300 DPI")],
                                          string=u"Format de l'étiquette", default='PDF_10x15_300dpi')
    returnTypeChoice = fields.Selection([('2', u"Retour payant en prioritaire"),
                                         ('3', u"Ne pas retourner")],
                                        string=u"Retour à l'expéditeur", default='3')
    productCode = fields.Selection([('CORE', u"Retour Colissimo - France"),
                                    ('CORI', u"Retour Colissimo - International")],
                                   string=u"Produit souhaité", default='CORE', required=True)
    #TODO: manque un type d'envoi ?
    nonMachinable = fields.Selection([('false', "Dimensions standards"),
                                      ('true', "Dimensions non standards")],
                                     string="Dimensions", default='false')
    ftd = fields.Selection([('false', "Auto"), ('true', "Manuel")],
                           string=u"Droits de douane", default='false',
                           help=u"Sélectionnez manuel vous souhaitez prendre à votre charge les droits de douanes en "
                                u"cas de taxation des colis")

    @api.onchange('type')
    def onchange_type(self):
        for rec in self:
            if rec.type == 'france':
                rec.countryCode = 'FR'
            else:
                rec.countryCode = ''

    # A few functions to overwrite
    @api.multi
    def _get_order_data(self):
        return (False, False, False)

    @api.multi
    def get_output_file(self, direction):
        return "Etiquette Colissimo"

    @api.multi
    def create_attachment(self):
        return False

    @api.multi
    def generate_label(self):
        self.ensure_one()
        company = self.env['res.users'].browse(self.env.uid).company_id
        contractNumber = self.env['ir.config_parameter'].\
            get_param('generate_tracking_labels_colissimo.login_colissimo', default='')
        password = self.env['ir.config_parameter'].\
            get_param('generate_tracking_labels_colissimo.password_colissimo', default='')
        if self.codeBarForReference == 'true' and self.productCode != 'CORE':
            raise exceptions.except_orm('Erreur!', "Impossible d'afficher le code barre retour pour un autre "
                                                   "produit que Colissimo retour")
        if self.serviceInfo and self.productCode != 'CORE':
            raise exceptions.except_orm('Erreur!', "Impossible de définir un nom de service en retour pour un "
                                                   "autre produit que Colissimo retour")
        depositDate = fields.Date.today()
        x = 0
        y = 0
        mailBoxPicking = 'false'
        #TODO: veut-on faire du mailBoxPicking ?

        # Order data
        transportationAmount, totalAmount, orderNumber = self._get_order_data()

        commercialName = company.name or ''
        senderParcelRef = orderNumber

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
        phoneNumber2 = company.phone or ''
        mobileNumber2 = ''
        doorCode12 = ''
        doorCode22 = ''
        email2 = company.email or ''
        intercom2 = ''
        language2 = 'FR'

#TODO: returntype (si on veut aussi que l'étiquette soit envoyée à une certaine adresse mail),
#TODO: pickuplocationid (identifiant du point de retrait), bloc custom (douane)


        first_part = (contractNumber,password, x, y, self.outputPrintingType, self.productCode, depositDate,
                      mailBoxPicking, transportationAmount, totalAmount, orderNumber, commercialName,
                      self.returnTypeChoice, self.weight, self.nonMachinable, self.instructions, self.ftd,
                      senderParcelRef)

        customer_data = (self.companyName or '', self.lastName or '', self.firstName or '', self.line0 or '',
                         self.line1 or '', self.line2 or '', self.line3 or '', self.countryCode or '', self.city or '',
                         self.zipCode or '', self.phoneNumber or '', self.mobileNumber or '', self.doorCode1 or '',
                         self.doorCode2 or '', self.email or '', self.intercom or '', self.language)

        second_part = (self.adresseeParcelRef or '', self.codeBarForReference or '', self.serviceInfo or '')

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
        if len(response.text.encode('utf-8').split('<pdfUrl>')) == 2 and\
            len(response.text.encode('utf-8').split('<pdfUrl>')[1].split('</pdfUrl>')) == 2:
            tracking_number = response.text.encode('utf-8').split('<parcelNumber>')[1].split('</parcelNumber>')[0]
            url = response.text.encode('utf-8').split('<pdfUrl>')[1].split('</pdfUrl>')[0].replace('amp;', '')
            file = urlopen(url)
            outputfile = self.get_output_file(self.direction)
            self.create_attachment(outputfile, file, self.direction)
            return tracking_number, self.save_tracking_number, self.direction, url
        elif len(response.text.encode('utf-8').split('<messageContent>')) == 2 and\
            len(response.text.encode('utf-8').split('<messageContent>')[1].split('</messageContent>')) == 2:
            raise exceptions.except_orm('Erreur!', response.text.encode('utf-8').
                                        split('<messageContent>')[1].split('</messageContent>')[0])
        else:
            raise exceptions.except_orm('Erreur!', "Impossible de générer l'étiquette")


class GenerateTrackingLabelsIrAttachment(models.Model):
    _inherit = 'ir.attachment'

    direction = fields.Selection([('to_customer', "Va vers le client"), ('from_customer', "Vient du client")],
                                 required=True)
