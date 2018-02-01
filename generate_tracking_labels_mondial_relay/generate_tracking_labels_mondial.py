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
from .mondialrelay_pyt import MRWebService
from openerp import models, api, fields, tools
from openerp.exceptions import UserError
from openerp.tools import ustr


class GenerateTrackingLabelsWizardMR(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    @api.multi
    def generate_label(self):
        result = super(GenerateTrackingLabelsWizardMR, self).generate_label()
        if self.transporter_id == self.env.ref('base_delivery_tracking_mondial_relay.transporter_mondial_relay'):
            login_mondial = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_mondial_relay.login_mondial', default='')
            password_mondial = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_mondial_relay.password_mondial', default='')
            societe_mondial = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_mondial_relay.societe_mondial', default='')
            marque_mondial = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_mondial_relay.marque_mondial', default='')
            code_marque_mondial = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_mondial_relay.code_marque_mondial', default='')
            origine_mondial = self.env['ir.config_parameter']. \
                get_param('generate_tracking_labels_mondial_relay.origine_mondial', default='')
            if not login_mondial or \
                    not password_mondial or \
                    not marque_mondial or \
                    not societe_mondial or \
                    not code_marque_mondial or \
                    not origine_mondial:
                raise UserError(u"Veuillez remplir la configuration Mondial relay")

            # evc_code : valeur unique
            packages_data = self.get_packages_data()


            company_name_1 = self.partner_orig_id.company_id.name
            company_civility = self.convert_title_chronopost(self.partner_orig_id.company_id.partner_id.title)
            company_name_2 = self.env.user.name
            shipper_name = ''
            company_adress_1 = self.partner_orig_id.street or ''
            company_adress_2 = self.partner_orig_id.street2 or ''
            company_zip = self.partner_orig_id.zip
            company_city = self.partner_orig_id.city
            company_country = self.partner_orig_id.country_id.code
            company_country_name = self.partner_orig_id.country_id.name.upper()
            company_phone = self.partner_orig_id.phone
            company_mobile_phone = self.partner_orig_id.mobile
            company_email = self.partner_orig_id.email


            customer_name_1 = self.company_name
            customer_civility = self.partner_id.name or ''
            customer_name_2 = self.partner_id.name or ''
            shipper_name_2 = self.partner_id.name or ''
            customer_adress_1 = self.line2 or ''
            customer_adress_2 = self.line3 or ''
            customer_zip = self.zip
            customer_city = self.city
            customer_country = self.country_id.code
            customer_country_name = self.country_id.name.upper()
            customer_phone = self.phone_number
            customer_mobile_phone = self.mobile_number
            customer_email = self.email

            # TODO: calculer
            recipient_ref = self.partner_id.id_relais
            customer_sky_bill_number = ''

            number_of_parcel = len(packages_data)

            connexion = MRWebService(password_mondial)
            vals = {
                'Enseigne': login_mondial,
                'ModeCol': 'CCC',
                'ModeLiv': self.produit_expedition_id.code,
                'NClient': '123456789',
                'Expe_Langage': 'FR',
                'Expe_Ad1': company_name_1,
                'Expe_Ad2': '',
                'Expe_Ad3': company_adress_1,
                'Expe_Ad4': company_adress_2,
                'Expe_Ville': company_city,
                'Expe_CP': company_zip,
                'Expe_Pays': company_country,
                'Expe_Tel1': company_phone or '',
                'Dest_Langage': 'FR',
                'Dest_Ad1': 'M.%s' % customer_name_2,
                'Dest_Ad2': customer_name_1,
                'Dest_Ad3': customer_adress_1,
                'Dest_Ad4': customer_adress_2,
                'Dest_Ville': customer_city,
                'Dest_CP': customer_zip,
                'Dest_Pays': customer_country,
                'Dest_Tel1': customer_phone or '',
                "LIV_Rel_Pays": customer_country,
                'LIV_Rel': recipient_ref,
                'Poids': str(int(self.weight*1000)),
                'NbColis': str(number_of_parcel),
                'CRT_Valeur': str(int(sum([package_data['amount_total'] for package_data in packages_data])*100))
            }
            reqst = connexion.make_shipping_label(vals, labelformat=self.output_printing_type_id.code)
            if reqst and reqst.get("ExpeditionNum") and reqst.get("URL_Etiquette"):
                reservation_number = reqst.get("ExpeditionNum")
                tracking_numbers = [reservation_number]
                label = requests.get(reqst.get("URL_Etiquette"))
                if len(label.content.split('%PDF')) == 2 and label.content.split('%PDF')[1].split('%EOF'):
                    pdf_binary_string = '%PDF' + label.content.split('%PDF')[1].split('%EOF')[0] + '%EOF' + '\n'
                    self.create_attachment([pdf_binary_string])
                    return tracking_numbers
            else:
                raise UserError(u"Impossible de générer l'étiquette")
        return result
