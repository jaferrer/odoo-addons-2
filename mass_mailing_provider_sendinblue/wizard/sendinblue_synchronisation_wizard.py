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

from __future__ import print_function

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from odoo import fields, models, api


class SendinblueSynchronisationWizard(models.TransientModel):
    _name = 'sendinblue.sync.wizard'
    _description = 'Sendinblue synchronisation wizard'

    synchronize_mass_mailing = fields.Boolean("Mass mailings", default=True)
    synchronize_contact = fields.Boolean("Contacts", default=True)
    synchronize_list = fields.Boolean("Lists", default=True)
    synchronize_campaign = fields.Boolean("Campaigns", default=True)
    synchronize_folders = fields.Boolean("Folders", default=True)

    @api.model
    def get_sendinblue_api_configuration(self):
        """
        Configure API key authorization: api-key & partner-key.
        """
        configuration = sib_api_v3_sdk.Configuration()
        # test api_key : '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'
        api_key = self.env['ir.config_parameter'].sudo().get_param('sendinblue_api_key')
        configuration.api_key['api-key'] = api_key
        configuration.api_key['partner-key'] = api_key

        return configuration

    @api.multi
    def button_do_send_infos_to_sendinblue(self):
        self.ensure_one()
        if self.synchronize_mass_mailing:
            self.synchronize_smtp_with_sendinblue()
        if self.synchronize_contact:
            self.synchronize_contacts_with_sendinblue()
        if self.synchronize_list:
            self.synchronize_lists_with_sendinblue()
        if self.synchronize_campaign:
            self.synchronize_campaign_with_sendinblue()
        if self.synchronize_folders:
            self.synchronize_folders_with_sendinblue()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def synchronize_smtp_with_sendinblue(self):
        """
        Synchronize Sendinblue mail templates with Odoo. Two cases depending on res config settings:
        - Odoo > Sendinblue.
        - Sendinblue > Odoo.
        """
        api_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))

        if not self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_smtp'):
            self.synchronize_smtp_odoo_priority(api_instance)
        else:
            self.synchronize_smtp_sendinblue_priority(api_instance)

    @api.model
    def synchronize_smtp_odoo_priority(self, api_instance):
        """
        Odoo > Sendinblue.
        """
        for odoo_smtp in self.env['mail.mass_mailing'].search([('supplier', '=', 'sendinblue')]):
            # Sendinblue smtp creation from Odoo (recreate if smtp suppressed in Sendinblue)
            try:
                sendinblue_smtp_info = api_instance.get_smtp_template(odoo_smtp.id_sendinblue_tmpl)
            except ApiException:
                sendinblue_smtp_info = False

            if not odoo_smtp.id_sendinblue_tmpl or not sendinblue_smtp_info:
                odoo_smtp.create_smtp_sendinblue(api_instance, self)
            else:
                odoo_smtp.update_smtp_sendinblue(api_instance)

        # If no smtp in Sendinblue, it sends an error...
        try:
            sendinblue_smtps = api_instance.get_smtp_templates(template_status='true')
            for sib_smtp in sendinblue_smtps.templates:
                if not self.env['mail.mass_mailing'].search([('id_sendinblue_tmpl', '=', sib_smtp.id)]):
                    smtp_template = sib_api_v3_sdk.UpdateSmtpTemplate(is_active=False)
                    api_instance.update_smtp_template(sib_smtp.id, smtp_template)
                    api_instance.delete_smtp_template(sib_smtp.id)
        except ValueError:
            pass

    @api.model
    def synchronize_smtp_sendinblue_priority(self, api_instance):
        """
        Sendinblue > Odoo.
        """
        sendinblue_smtps = api_instance.get_smtp_templates(template_status='true')
        already_treated_odoo_smtp = self.env['mail.mass_mailing']
        # If no smtp Sendinblue, all Odoo's are suppressed
        if not sendinblue_smtps.templates:
            self.env['mail.mass_mailing'].search([]).unlink()
        else:
            for sib_smtp in sendinblue_smtps.templates:
                odoo_smtp = self.env['mail.mass_mailing'].search([('id_sendinblue_tmpl', '=', sib_smtp.id)])
                if not odoo_smtp:
                    already_treated_odoo_smtp |= self.env['mail.mass_mailing'].create({
                        'id_sendinblue_tmpl': sib_smtp.id,
                        'name': sib_smtp.subject,
                        'body_html': sib_smtp.html_content,
                        'reply_to': sib_smtp.reply_to
                    })
                else:
                    already_treated_odoo_smtp |= odoo_smtp
                    odoo_smtp.write({
                        'name': sib_smtp.subject,
                        'body_html': sib_smtp.html_content,
                        'reply_to': sib_smtp.reply_to,
                    })

        for odoo_smtp in self.env['mail.mass_mailing'].search([('id', 'not in', already_treated_odoo_smtp.ids)]):
            if not odoo_smtp.id_sendinblue_tmpl:
                odoo_smtp.unlink()
            else:
                try:
                    api_instance.get_smtp_template(odoo_smtp.id_sendinblue_tmpl)
                except ApiException:
                    odoo_smtp.unlink()

    @api.model
    def synchronize_contacts_with_sendinblue(self):
        """
        Synchronize Sendinblue contacts with Odoo. Two cases depending on res config settings:
        - Odoo > Sendinblue.
        - Sendinblue > Odoo.
        """
        api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))

        if not self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_contact'):
            self.synchronize_contact_odoo_priority(api_instance)
        else:
            self.synchronize_contact_sendinblue_priority(api_instance)

    @api.model
    def synchronize_contact_odoo_priority(self, api_instance):
        """
        Odoo > Sendinblue.
        """
        for odoo_contact in self.env['mail.mass_mailing.contact'].search([]):
            # Sendinblue contacts creation from Odoo (recreate if contact suppressed in Sendinblue)
            try:
                sendinblue_contact_info = api_instance.get_contact_info(odoo_contact.email)
            except ApiException:
                sendinblue_contact_info = False

            if not odoo_contact.id_sendinblue_contact or not sendinblue_contact_info:
                odoo_contact.create_contact_sendinblue(api_instance)
            else:
                odoo_contact.update_contact_sendinblue(api_instance)

        # If no contact in Sendinblue, it sends an error...
        try:
            sendinblue_contacts = api_instance.get_contacts()
            for sib_contact in sendinblue_contacts.contacts:
                # Attention au contact du compte, on ne peut pas le supprimer
                if sib_contact.get('id') != 1 and not self.env['mail.mass_mailing.contact'].search([
                    ('email', '=', sib_contact.get('email'))
                ]):
                    api_instance.delete_contact(sib_contact.get('email'))
        except ValueError:
            pass

    @api.model
    def synchronize_contact_sendinblue_priority(self, api_instance):
        """
        Sendinblue > Odoo.
        """
        sendinblue_contacts = api_instance.get_contacts()
        already_treated_odoo_contacts = self.env['mail.mass_mailing.contact']
        # If no smtp Sendinblue, all Odoo's are suppressed
        if not sendinblue_contacts.contacts:
            self.env['mail.mass_mailing.contact'].search([]).unlink()
        else:
            for sib_contact in sendinblue_contacts.contacts:
                odoo_contact = self.env['mail.mass_mailing.contact'].search([
                    ('id_sendinblue_contact', '=', sib_contact.get('id'))
                ])
                if not odoo_contact:
                    already_treated_odoo_contacts |= self.env['mail.mass_mailing.contact'].create({
                        'id_sendinblue_contact': sib_contact.get('id'),
                        'email': sib_contact.get('email'),
                        'name': sib_contact.get('attributes').get('LASTNAME'),
                    })
                else:
                    already_treated_odoo_contacts |= odoo_contact
                    odoo_contact.write({
                        'email': sib_contact.get('email'),
                        'name': sib_contact.get('attributes').get('LASTNAME'),
                    })

        for odoo_contact in self.env['mail.mass_mailing.contact'].search([
            ('id', 'not in', already_treated_odoo_contacts.ids)
        ]):
            if not odoo_contact.id_sendinblue_contact:
                odoo_contact.unlink()
            else:
                try:
                    api_instance.get_contact(odoo_contact.email)
                except ApiException:
                    odoo_contact.unlink()

    @api.model
    def synchronize_lists_with_sendinblue(self):
        """
        Synchronize Sendinblue lists with Odoo. Two cases depending on res config settings:
        - Odoo > Sendinblue.
        - Sendinblue > Odoo.
        """
        api_instance = sib_api_v3_sdk.ListsApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))

        if not self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_list'):
            self.synchronize_lists_odoo_priority(api_instance)
        else:
            self.synchronize_lists_sendinblue_priority(api_instance)

    @api.model
    def synchronize_lists_odoo_priority(self, api_instance):
        """
        Odoo > Sendinblue.
        """
        for odoo_list in self.env['mail.mass_mailing.list'].search([]):
            # Sendinblue list creation from Odoo (recreate if list suppressed in Sendinblue)
            try:
                sendinblue_list_info = api_instance.get_list(odoo_list.id_sendinblue_list)
            except ApiException:
                sendinblue_list_info = False
            if not odoo_list.id_sendinblue_list or not sendinblue_list_info:
                odoo_list.create_list_sendinblue(api_instance, self)
            else:
                odoo_list.update_list_sendinblue(api_instance)

        # If no list in Sendinblue, it sends an error...
        try:
            sendinblue_lists = api_instance.get_lists()
            for sib_list in sendinblue_lists.lists:
                if not self.env['mail.mass_mailing.list'].search([('id_sendinblue_list', '=', sib_list.get('id'))]):
                    api_instance.delete_list(sib_list.get('id'))
        except ValueError:
            pass

    @api.model
    def synchronize_lists_sendinblue_priority(self, api_instance):
        """
        Sendinblue > Odoo.
        """
        try:
            sendinblue_lists = api_instance.get_lists()
        except ValueError:
            # If no list in Sendinblue, all Odoo's are suppressed
            sendinblue_lists = False
            self.env['mail.mass_mailing.list'].search([]).unlink()
        already_treated_odoo_lists = self.env['mail.mass_mailing.list']
        if sendinblue_lists:
            for sib_list in sendinblue_lists.lists:
                odoo_list = self.env['mail.mass_mailing.list'].search([('id_sendinblue_list', '=', sib_list.get('id'))])
                if not odoo_list:
                    already_treated_odoo_lists |= self.env['mail.mass_mailing.list'].create({
                        'id_sendinblue_list': sib_list.get('id'),
                        'name': sib_list.get('name'),
                        'folder_id': sib_list.get('folder_id'),
                    })
                else:
                    already_treated_odoo_lists |= odoo_list
                    odoo_list.write({
                        'name': sib_list.get('name'),
                        'folder_id': sib_list.get('folder_id'),
                    })

        for odoo_list in self.env['mail.mass_mailing.list'].search([('id', 'mot in', already_treated_odoo_lists.ids)]):
            if not odoo_list.id_sendinblue_list:
                odoo_list.unlink()
            else:
                try:
                    api_instance.get_list(odoo_list.id_sendinblue_list)
                except ValueError:
                    odoo_list.unlink()

    @api.model
    def synchronize_campaign_with_sendinblue(self):
        """
        Synchronize Sendinblue campaigns with Odoo. Two cases depending on res config settings:
        - Odoo > Sendinblue.
        - Sendinblue > Odoo.
        """
        api_instance = sib_api_v3_sdk.EmailCampaignsApi(
            sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))

        if not self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_campaign'):
            self.synchronize_campaign_odoo_priority(api_instance)
        else:
            self.synchronize_campaign_sendinblue_priority(api_instance)

    @api.model
    def synchronize_campaign_odoo_priority(self, api_instance):
        """
        Odoo > Sendinblue.
        """
        odoo_campaigns = self.env['mail.mass_mailing.campaign'].search([
            ('medium_id', '=', self.env.ref('utm.utm_medium_email').id)
        ])
        if odoo_campaigns:
            for odoo_campaign in odoo_campaigns:
                # Sendinblue campaign creation from Odoo (recreate if campaign suppressed in Sendinblue)
                # get_email_campaign (for single campaign doesn't work properly)
                # probably because scheduled_at is not set so it tries to convert "" into datetime
                try:
                    sendinblue_campaigns = api_instance.get_email_campaigns()
                    sendinblue_campaign_info = False
                    for sib_campaign in sendinblue_campaigns.campaigns:
                        if sib_campaign.get('id') == odoo_campaign.id_sendinblue_campaign:
                            sendinblue_campaign_info = sib_campaign
                            continue
                except ValueError:
                    sendinblue_campaigns = False
                    sendinblue_campaign_info = False

                if not odoo_campaign.id_sendinblue_campaign or not sendinblue_campaign_info:
                    odoo_campaign.create_campaign_sendinblue(api_instance, self)
                else:
                    odoo_campaign.update_campaign_sendinblue(api_instance, self)

            if sendinblue_campaigns:
                for sib_campaign in sendinblue_campaigns.campaigns:
                    if not self.env['mail.mass_mailing.campaign'].search([
                        ('id_sendinblue_campaign', '=', sib_campaign.get('id'))
                    ]):
                        api_instance.delete_email_campaign(sib_campaign.get('id'))
        else:
            sendinblue_campaigns = api_instance.get_email_campaigns()
            for sib_campaign in sendinblue_campaigns.campaigns:
                api_instance.delete_email_campaign(sib_campaign.get('id'))

    @api.model
    def synchronize_campaign_sendinblue_priority(self, api_instance):
        """
        Sendinblue > Odoo.
        """
        try:
            sendinblue_campaigns = api_instance.get_email_campaigns()
        except ValueError:
            # If no Sendinblue campaign, all Odoo's are suppressed
            sendinblue_campaigns = False
            self.env['mail.mass_mailing.campaign'].search([]).unlink()

        already_treated_odoo_campaigns = self.env['mail.mass_mailing.campaign']
        if sendinblue_campaigns:
            for sib_campaign in sendinblue_campaigns.campaigns:
                odoo_campaign = self.env['mail.mass_mailing.campaign'].search([
                    ('id_sendinblue_campaign', '=', sib_campaign.get('id'))
                ])
                odoo_campaign_smtp = self.env['mail.mass_mailing'].search([
                    ('body_html', '=', sib_campaign.get('htmlContent'))
                ])
                if not odoo_campaign:
                    already_treated_odoo_campaigns |= self.env['mail.mass_mailing.campaign'].create({
                        'id_sendinblue_campaign': sib_campaign.get('id'),
                        'name': sib_campaign.get('subject'),
                        'mass_mailing_id': odoo_campaign_smtp.id,
                    })
                else:
                    already_treated_odoo_campaigns |= odoo_campaign
                    odoo_campaign.write({
                        'name': sib_campaign.get('subject'),
                        'mass_mailing_id': odoo_campaign_smtp.id,
                    })

        for odoo_campaign in self.env['mail.mass_mailing.campaign'].search([
            ('id', 'not in', already_treated_odoo_campaigns.ids)
        ]):
            if not odoo_campaign.id_sendinblue_campaign:
                odoo_campaign.unlink()
            else:
                try:
                    api_instance.get_email_campaign(odoo_campaign.id_sendinblue_campaign)
                except ApiException:
                    odoo_campaign.unlink()

    @api.model
    def synchronize_folders_with_sendinblue(self):
        """
        Synchronize Sendinblue folders with Odoo. Two cases depending on res config settings:
        - Odoo > Sendinblue.
        - Sendinblue > Odoo.
        """
        api_instance = sib_api_v3_sdk.FoldersApi(sib_api_v3_sdk.ApiClient(self.get_sendinblue_api_configuration()))

        if not self.env['ir.config_parameter'].sudo().get_param('priorize_sendinblue_folder'):
            self.synchronize_folders_odoo_priority(api_instance)
        else:
            self.synchronize_folders_sendinblue_priority(api_instance)

    @api.model
    def synchronize_folders_odoo_priority(self, api_instance):
        """
        Odoo > Sendinblue.
        """
        for odoo_folder in self.env['mail.mass_mailing.folder'].search([]):
            # Sendinblue folder creation from Odoo (recreate if folder suppressed in Sendinblue)
            if odoo_folder.id_sendinblue_folder:
                try:
                    sendinblue_folder_info = api_instance.get_folder(odoo_folder.id_sendinblue_folder)
                except ApiException:
                    sendinblue_folder_info = False
            else:
                sendinblue_folder_info = False

            if not odoo_folder.id_sendinblue_folder or not sendinblue_folder_info:
                odoo_folder.create_folder_sendinblue(api_instance)
            else:
                # Impossible de renommer un dossier Sendinblue à partir d'Odoo, il faut en créer un nouveau...
                # Ces données sont propres à Sendinblue
                odoo_folder.write({
                    'name': sendinblue_folder_info.name,
                    'total_blacklisted': sendinblue_folder_info.total_blacklisted,
                    'total_subscribers': sendinblue_folder_info.total_subscribers,
                    'unique_subscribers': sendinblue_folder_info.unique_subscribers,
                })

        # If no folder in Sendinblue, it sends an error...
        try:
            # Sendinblue folder suppression from Odoo only
            sendinblue_folders = api_instance.get_folders(limit=50, offset=0)
            for sib_folder in sendinblue_folders.folders:
                if not self.env['mail.mass_mailing.folder'].search([
                    ('id_sendinblue_folder', '=', sib_folder.get('id'))
                ]):
                    api_instance.delete_folder(sib_folder.get('id'))
        except ValueError:
            pass

    @api.model
    def synchronize_folders_sendinblue_priority(self, api_instance):
        """
        Sendinblue > Odoo.
        """
        sendinblue_folders = api_instance.get_folders(limit=50, offset=0)
        already_treated_odoo_folder = self.env['mail.mass_mailing.folder']
        # If no folder Sendinblue, all Odoo's are suppressed
        if not sendinblue_folders.folders:
            self.env['mail.mass_mailing.folder'].search([]).unlink()
        else:
            for sib_folder in sendinblue_folders.folders:
                odoo_folder = self.env['mail.mass_mailing.folder'].search([
                    ('id_sendinblue_folder', '=', sib_folder.get('id'))
                ])
                if not odoo_folder:
                    already_treated_odoo_folder |= self.env['mail.mass_mailing.folder'].create({
                        'id_sendinblue_folder': sib_folder.get('id'),
                        'name': sib_folder.get('name'),
                        'total_blacklisted': sib_folder.get('total_blacklisted'),
                        'total_subscribers': sib_folder.get('total_subscribers'),
                        'unique_subscribers': sib_folder.get('unique_subscribers'),
                    })
                else:
                    already_treated_odoo_folder |= odoo_folder
                    odoo_folder.write({
                        'name': sib_folder.get('name'),
                        'total_blacklisted': sib_folder.get('total_blacklisted'),
                        'total_subscribers': sib_folder.get('total_subscribers'),
                        'unique_subscribers': sib_folder.get('unique_subscribers'),
                    })

        for odoo_folder in self.env['mail.mass_mailing.folder'].search([
            ('id', 'not in', already_treated_odoo_folder.ids)
        ]):
            if not odoo_folder.id_sendinblue_folder:
                odoo_folder.unlink()
            else:
                try:
                    api_instance.get_folder(odoo_folder.id_sendinblue_folder)
                except ApiException:
                    odoo_folder.unlink()
