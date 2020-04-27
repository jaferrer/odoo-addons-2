# # -*- coding: utf8 -*-
# #
# # Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
# #
# #    This program is free software: you can redistribute it and/or modify
# #    it under the terms of the GNU Affero General Public License as
# #    published by the Free Software Foundation, either version 3 of the
# #    License, or (at your option) any later version.
# #
# #    This program is distributed in the hope that it will be useful,
# #
# #    but WITHOUT ANY WARRANTY; without even the implied warranty of
# #    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# #    GNU Affero General Public License for more details.
# #
# #    You should have received a copy of the GNU Affero General Public License
# #    along with this program.  If not, see <http://www.gnu.org/licenses/>.
# #
#
# from __future__ import print_function
#
# import dateutil
# import sib_api_v3_sdk
# from sib_api_v3_sdk.rest import ApiException
#
# from odoo.exceptions import UserError
# from odoo import fields, models, api
#
#
# class SendinblueSynchronisationWizard(models.TransientModel):
#     _name = 'sendinblue.sync.wizard'
#     _description = 'Sendinblue synchronisation wizard'
#
#     synchronize_mass_mailing = fields.Boolean("Mass mailings", default=False)
#     synchronize_contact = fields.Boolean("Contacts", default=False)
#     synchronize_list = fields.Boolean("Lists", default=True)
#     synchronize_campaign = fields.Boolean("Campaigns", default=False)
#     synchronize_folders = fields.Boolean("Folders", default=False)
#
#     @api.model
#     def get_sendinblue_api_configuration(self):
#         """
#         Configure API key authorization: api-key & partner-key.
#         """
#         configuration = sib_api_v3_sdk.Configuration()
#         # test api_key : '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'
#         api_key = self.env['ir.config_parameter'].sudo().get_param('sendinblue_api_key')
#         configuration.api_key['api-key'] = api_key
#         configuration.api_key['partner-key'] = api_key
#
#         return configuration
#
#     @api.model
#     def create_contact_attributes(self):
#         api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         create_attribute_text = sib_api_v3_sdk.CreateAttribute(type='text')
#         # create_attribute_date = sib_api_v3_sdk.CreateAttribute(type='date')
#         try:
#             api_instance.create_attribute("normal", "TITLE", create_attribute_text)
#             api_instance.create_attribute("normal", "COMPANY_NAME", create_attribute_text)
#             api_instance.create_attribute("normal", "COUNTRY", create_attribute_text)
#             api_instance.create_attribute("normal", "WRITE_DATE_SENDINBLUE", create_attribute_text)
#             api_instance.create_attribute("normal", "ODOO_CONTACT_ID", create_attribute_text)
#         except ApiException as error_msg:
#             raise UserError("Exception when calling ContactsApi -> create_attribute : %s\n" % error_msg)
#
#     @api.multi
#     def button_do_send_infos_to_sendinblue(self):
#         self.ensure_one()
#         if self.synchronize_mass_mailing:
#             self.synchronize_smtp_with_sendinblue()
#         if self.synchronize_contact:
#             self.synchronize_contacts_with_sendinblue()
#         if self.synchronize_list:
#             self.synchronize_lists_with_sendinblue()
#         if self.synchronize_campaign:
#             self.synchronize_campaign_with_sendinblue()
#         if self.synchronize_folders:
#             self.synchronize_folders_with_sendinblue()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'reload',
#         }
#
#     @api.model
#     def synchronize_smtp_with_sendinblue(self):
#         """
#         - Send new Odoo mail templates to Sendinblue.
#         - Update common mail templates depending on last modification date.
#         - Supress all new Sendinblue mail templates not related to an Odoo mail template.
#         -> Creation and suppression are unidirectionnal (Odoo > Sendinblue) because we can't add any parameter to a
#         Sendinblue smtp.
#         """
#         api_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         for odoo_smtp in self.env['mail.mass_mailing'].search(['supplier', '=', 'sendinblue']):
#
#             # Sendinblue smtp creation from Odoo only (recreate if smtp suppressed in Sendinblue)
#             try:
#                 sendinblue_smtp_info = api_instance.get_smtp_template(odoo_smtp.id_sendinblue_tmpl)
#             except ApiException:
#                 sendinblue_smtp_info = False
#             if not odoo_smtp.id_sendinblue_tmpl or not sendinblue_smtp_info:
#                 odoo_smtp.create_smtp_sendinblue(api_instance, self)
#             else:
#                 sendinblue_write_date = fields.Datetime.to_string(sendinblue_smtp_info.modified_at)
#                 odoo_correct_date = fields.Datetime.to_string(
#                     self.env.user.localize_date(odoo_smtp.write_date_sendinblue))
#
#                 # Last update in Odoo
#                 if odoo_correct_date > sendinblue_write_date:
#                     odoo_smtp.update_smtp_sendinblue(api_instance)
#
#                 # Last update in Sendinblue
#                 elif odoo_correct_date < sendinblue_write_date:
#                     odoo_smtp.update_smtp_odoo(sendinblue_smtp_info, sendinblue_write_date)
#
#         # If no smtp in Sendinblue, it sends an error...
#         try:
#             # Sendinblue smtp suppression from Odoo only
#             sendinblue_smtps = api_instance.get_smtp_templates(template_status='true', limit=50, offset=0)
#             for sib_smtp in sendinblue_smtps.templates:
#                 if not self.env['mail.mass_mailing'].search([('id_sendinblue_tmpl', '=', sib_smtp.id)]):
#                     smtp_template = sib_api_v3_sdk.UpdateSmtpTemplate(is_active=False)
#                     api_instance.update_smtp_template(sib_smtp.id, smtp_template)
#                     api_instance.delete_smtp_template(sib_smtp.id)
#         except ValueError:
#             pass
#
#     @api.model
#     def synchronize_contacts_with_sendinblue(self):
#         """
#         - Send new Odoo contacts to Sendinblue.
#         - Update common contacts depending on last modification date.
#         - Send new Sendinblue contacts to Odoo.
#         """
#         api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         for odoo_contact in self.env['mail.mass_mailing.contact'].search([]):
#
#             # Sendinblue contact creation from Odoo
#             if not odoo_contact.id_sendinblue_contact:
#                 odoo_contact.create_contact_sendinblue(api_instance)
#
#             else:
#                 sendinblue_contact_info = api_instance.get_contact_info(odoo_contact.email)
#                 sendinblue_write_date = sendinblue_contact_info.attributes.get('WRITE_DATE_SENDINBLUE')
#                 sendinblue_write_date_dt = dateutil.parser.parse(sendinblue_write_date)
#                 odoo_correct_date = self.env.user.localize_date(odoo_contact.write_date_sendinblue)
#
#                 # Last update in Odoo
#                 if odoo_correct_date > sendinblue_write_date_dt:
#                     odoo_contact.update_contact_sendinblue(api_instance, odoo_correct_date)
#
#                 # Last update in Sendinblue
#                 elif odoo_correct_date < sendinblue_write_date_dt:
#                     odoo_contact.update_contact_odoo(sendinblue_contact_info, sendinblue_write_date_dt)
#
#         # Odoo contact creation from Sendinblue
#         try:
#             sendinblue_contacts = api_instance.get_contacts(limit=50, offset=0)
#             for sib_contact in sendinblue_contacts.contacts:
#                 # A Sendinblue contact with odoo_contact_id but without related Odoo contact is suppressed
#                 if sib_contact.get('attributes').get('ODOO_CONTACT_ID'):
#                     if not self.env['mail.mass_mailing.contact'].search([('email', '=', sib_contact.get('email'))]):
#                         api_instance.delete_contact(sib_contact.get('email'))
#                 # New Sendinblue contacts should not have an odoo_contact_id (To handle contact suppression)
#                 else:
#                     if not self.env['mail.mass_mailing.contact'].search([('email', '=', sib_contact.get('email'))]):
#                         self.env['mail.mass_mailing.contact'].create_contact_odoo(api_instance, sib_contact)
#                     else:
#                         raise UserError("Problème de synchronisation avec le contact %s. Il ne possède pas d'Odoo id "
#                                         "alors que ce contact existe dans Odoo" % sib_contact.get('email'))
#         # If no contact in Sendinblue, it sends an error...
#         except ValueError:
#             pass
#
#     @api.model
#     def synchronize_lists_with_sendinblue(self):
#         """
#         - Send new Odoo lists to Sendinblue.
#         - Update common lists depending on last modification date.
#         - Supress all new Sendinblue lists not related to an Odoo list.
#        -> Creation modification and suppression are unidirectionnal (Odoo > Sendinblue) because we can't add any
#         parameter to a Sendinblue list and there is not even a modification date.
#         """
#         api_instance = sib_api_v3_sdk.ListsApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         if not self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_list'):
#             self.synchronize_lists_odoo_priority(api_instance)
#         else:
#             self.synchronize_lists_sendinblue_priority(api_instance)
#
#     @api.model
#     def synchronize_lists_odoo_priority(self, api_instance):
#         """
#         Odoo > Sendinblue.
#         """
#         for odoo_list in self.env['mail.mass_mailing.list'].search([]):
#             # Sendinblue list creation from Odoo (recreate if list suppressed in Sendinblue)
#             try:
#                 sendinblue_list_info = api_instance.get_list(odoo_list.id_sendinblue_list)
#             except ApiException:
#                 sendinblue_list_info = False
#             if not odoo_list.id_sendinblue_list or not sendinblue_list_info:
#                 odoo_list.create_list_sendinblue(api_instance, self)
#             else:
#                 odoo_list.update_list_sendinblue(api_instance)
#
#         # If no list in Sendinblue, it sends an error...
#         try:
#             sendinblue_lists = api_instance.get_lists()
#             for sib_list in sendinblue_lists.lists:
#                 if not self.env['mail.mass_mailing.list'].search([('id_sendinblue_list', '=', sib_list.get('id'))]):
#                     api_instance.delete_list(sib_list.get('id'))
#         except ValueError:
#             pass
#
#     @api.model
#     def synchronize_lists_sendinblue_priority(self, api_instance):
#         """
#         Sendinblue > Odoo.
#         """
#         try:
#             sendinblue_lists = api_instance.get_lists()
#         except ValueError:
#             # Si aucune liste dans Sendinblue, on supprime celles d'Odoo
#             sendinblue_lists = False
#             self.env['mail.mass_mailing.list'].search([]).unlink()
#         if sendinblue_lists:
#             for sib_list in sendinblue_lists.lists:
#                 odoo_list = self.env['mail.mass_mailing.list'].search([('id_sendinblue_list', '=', sib_list.get('id')
#                 )])
#                 if not odoo_list:
#                     self.env['mail.mass_mailing.list'].create({
#                         'id_sendinblue_list': sib_list.get('id'),
#                         'name': sib_list.get('name'),
#                         'folder_id': sib_list.get('folder_id'),
#                     })
#                 else:
#                     odoo_list.write({
#                         'name': sib_list.get('name'),
#                         'folder_id': sib_list.get('folder_id'),
#                     })
#
#         for odoo_list in self.env['mail.mass_mailing.list'].search([]):
#             if not odoo_list.id_sendinblue_list:
#                 odoo_list.unlink()
#             else:
#                 try:
#                     api_instance.get_list(odoo_list.id_sendinblue_list)
#                 except ValueError:
#                     odoo_list.unlink()
#
#     @api.model
#     def synchronize_campaign_with_sendinblue(self):
#         """
#         - Send new Odoo campaign to Sendinblue.
#         - Update common campaign depending on last modification date.
#         - Send new Sendinblue campaign to Odoo.
#         -> Creation and suppression are unidirectionnal (Odoo > Sendinblue) because we can't add any parameter to a
#         Sendinblue campaign.
#         """
#         api_instance = sib_api_v3_sdk.EmailCampaignsApi(
#             sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         for odoo_campaign in self.env['mail.mass_mailing.campaign'].search([
#             ('medium_id', '=', self.env.ref('utm.utm_medium_email').id)
#         ]):
#             # Sendinblue smtp creation from Odoo only (recreate if campaign suppressed in Sendinblue)
#             # get_email_campaign (for single campaign doesn't work properly)
#             # probably because scheduled_at is not set so it tries to convert "" into datetime
#             try:
#                 sendinblue_campaigns = api_instance.get_email_campaigns()
#                 sendinblue_campaign_info = False
#                 for sib_campaign in sendinblue_campaigns.campaigns:
#                     if sib_campaign.get('id') == odoo_campaign.id_sendinblue_campaign:
#                         sendinblue_campaign_info = sib_campaign
#                         continue
#             except ValueError:
#                 sendinblue_campaigns = False
#                 sendinblue_campaign_info = False
#             if not odoo_campaign.id_sendinblue_campaign or not sendinblue_campaign_info:
#                 odoo_campaign.create_campaign_sendinblue(api_instance, self)
#
#             else:
#                 sendinblue_write_date_tz = dateutil.parser.parse(sendinblue_campaign_info.get('modifiedAt'))
#                 sendinblue_write_date = fields.Datetime.from_string(fields.Datetime.to_string(sendinblue_write_date_tz
#                 ))
#                 odoo_correct_date = self.env.user.localize_date(odoo_campaign.write_date_sendinblue)
#
#                 # Last update in Odoo
#                 if odoo_correct_date > sendinblue_write_date:
#                     odoo_campaign.update_campaign_sendinblue(api_instance, self)
#
#                 # Last update in Sendinblue
#                 elif odoo_correct_date < sendinblue_write_date:
#                     odoo_campaign.update_campaign_odoo(sendinblue_campaign_info, sendinblue_write_date)
#
#         # Sendinblue campaign suppression from Odoo only
#         if sendinblue_campaigns:
#             for sib_campaign in sendinblue_campaigns.campaigns:
#                 if not self.env['mail.mass_mailing.campaign'].search(
#                         [('id_sendinblue_campaign', '=', sib_campaign.get('id'))]):
#                     api_instance.delete_email_campaign(sib_campaign.get('id'))
#
#     @api.model
#     def synchronize_folders_with_sendinblue(self):
#         """
#         - Send new Odoo folder to Sendinblue.
#         - Supress all new Sendinblue folder not related to an Odoo folder.
#         -> Creation modification and suppression are unidirectionnal (Odoo > Sendinblue) because we can't add any
#         parameter to a Sendinblue folder and there is not even a modification date.
#         """
#         api_instance = sib_api_v3_sdk.FoldersApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         for odoo_folder in self.env['mail.mass_mailing.folder'].search([]):
#
#             # Sendinblue folder creation from Odoo only (recreate if folder suppressed in Sendinblue)
#             try:
#                 sendinblue_folder_info = api_instance.get_folder(odoo_folder.id_sendinblue_folder)
#             except ApiException:
#                 sendinblue_folder_info = False
#             if not odoo_folder.id_sendinblue_folder or not sendinblue_folder_info:
#                 odoo_folder.create_folder_sendinblue(api_instance)
#             else:
#                 # No modification date in a Sendinblue folder -> Can't compare date -> (Odoo > Sendinblue)
#                 odoo_folder.update_folder_sendinblue(api_instance)
#
#         # If no folder in Sendinblue, it sends an error...
#         try:
#             # Sendinblue folder suppression from Odoo only
#             sendinblue_folders = api_instance.get_folders(limit=10, offset=0)
#             for sib_folder in sendinblue_folders.folders:
#                 if not self.env['mail.mass_mailing.folder'].search([('id_sendinblue_folder', '=', sib_folder.get('id')
#                 )]):
#                     api_instance.delete_folder(sib_folder.get('id'))
#         except ValueError:
#             pass

# @api.model
#     def create_contact_attributes(self):
#         api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))
#
#         create_attribute_text = sib_api_v3_sdk.CreateAttribute(type='text')
#         # create_attribute_date = sib_api_v3_sdk.CreateAttribute(type='date')
#         try:
#             api_instance.create_attribute("normal", "TITLE", create_attribute_text)
#             api_instance.create_attribute("normal", "COMPANY_NAME", create_attribute_text)
#             api_instance.create_attribute("normal", "COUNTRY", create_attribute_text)
#             api_instance.create_attribute("normal", "WRITE_DATE_SENDINBLUE", create_attribute_text)
#             api_instance.create_attribute("normal", "ODOO_CONTACT_ID", create_attribute_text)
#         except ApiException as error_msg:
#             raise UserError("Exception when calling ContactsApi -> create_attribute : %s\n" % error_msg)


# mass_mailing_provider_sendinblue.py
# @api.multi
#     def write(self, vals):
#         """
#         La date de modification Outlook est une date de modification qui peut-être imposée.
#         """
#         res = super(MassMailingProviderSendinblue, self).write(vals)
#
#         if not vals.get('write_date_sendinblue') and not self.env.context.get('creation'):
#             for rec in self:
#                 rec.write_date_sendinblue = rec.write_date
#
#         return res


# class MassMailingContactSendinblue(models.Model):
#     _inherit = 'mail.mass_mailing.contact'
#
#     id_sendinblue_contact = fields.Integer("Id contact Sendinblue", readonly=True, copy=False)
#
#     @api.multi
#     def create_contact_sendinblue(self, api_instance):
#         self.ensure_one()
#         create_contact = sib_api_v3_sdk.CreateContact(
#             attributes={
#                 'TITLE': self.title_id.name,
#                 'LASTNAME': self.name,
#                 'COMPANY_NAME': self.company_name,
#                 'COUNTRY': self.country_id.name,
#                 'ODOO_CONTACT_ID': self.id,
#             },
#             email=self.email,
#         )
#         try:
#             api_response = api_instance.create_contact(create_contact)
#             self.id_sendinblue_contact = api_response.id
#         except ApiException as error_msg:
#             raise UserError("Exception when calling ContactsApi -> create_contact : %s\n" % error_msg)
#
#     @api.multi
#     def update_contact_sendinblue(self, api_instance, odoo_correct_date):
#         self.ensure_one()
#         update_contact = sib_api_v3_sdk.UpdateContact({
#             'TITLE': self.title_id.name,
#             'LASTNAME': self.name,
#             'COMPANY_NAME': self.company_name,
#             'COUNTRY': self.country_id.name,
#             'WRITE_DATE_SENDINBLUE': odoo_correct_date,
#             'ODOO_CONTACT_ID': self.id,
#         })
#         try:
#             api_instance.update_contact(self.email, update_contact)
#         except ApiException as error_msg:
#             raise UserError("Exception when calling ContactsApi -> update_contact : %s\n" % error_msg)
#
#     @api.multi
#     def update_contact_odoo(self, sendinblue_contact_info, sendinblue_write_date_dt):
#         self.ensure_one()
#         title = self.env['res.partner.title'].search([
#             ('name', '=', sendinblue_contact_info.attributes.get('TITLE'))
#         ])
#         country = self.env['res.country'].search([
#             ('name', '=', sendinblue_contact_info.attributes.get('COUNTRY_NAME'))
#         ])
#         self.write({
#             'name': sendinblue_contact_info.attributes.get('LASTNAME'),
#             'title_id': title.id,
#             'company_name': sendinblue_contact_info.attributes.get('COMPANY_NAME'),
#             'country_id': country.id,
#         })
#
#     @api.model
#     def create_contact_odoo(self, api_instance, sendinblue_contact):
#         title = self.env['res.partner.title'].search([
#             ('name', '=', sendinblue_contact.get('attributes').get('TITLE'))
#         ])
#         country = self.env['res.country'].search([
#             ('name', '=', sendinblue_contact.get('attributes').get('COUNTRY'))
#         ])
#         last_write_dt = dateutil.parser.parse(sendinblue_contact.get('modifiedAt'))
#         last_write_dt = last_write_dt.replace(
#             tzinfo=last_write_dt.tzinfo).astimezone(pytz.UTC).replace(tzinfo=None)
#         odoo_contact = self.create({
#             'name': sendinblue_contact.get('attributes').get('LASTNAME'),
#             'email': sendinblue_contact.get('email'),
#             'title_id': title.id,
#             'company_name': sendinblue_contact.get('attributes').get('COMPANY_NAME'),
#             'country_id': country.id,
#             'id_sendinblue_contact': sendinblue_contact.get('id')
#         })
#
#         update_contact = sib_api_v3_sdk.UpdateContact({
#             'ODOO_CONTACT_ID': odoo_contact.id,
#         })
#         api_instance.update_contact(sendinblue_contact.get('email'), update_contact)
