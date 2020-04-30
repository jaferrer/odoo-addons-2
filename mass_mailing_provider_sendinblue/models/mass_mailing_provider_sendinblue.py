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

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from odoo.exceptions import UserError
from odoo import fields, models, api


class MassMailingProviderSendinblue(models.Model):
    _inherit = 'mail.mass_mailing'

    supplier = fields.Selection(selection_add=[('sendinblue', "Sendinblue")])
    id_sendinblue_tmpl = fields.Integer("Id mail template Sendinblue", readonly=True)

    @api.model
    def format_reply_to(self, reply_to):
        reply_to_splitted = reply_to.split()
        if len(reply_to_splitted) > 1:
            return reply_to_splitted[1].replace("<", "").replace(">", "")
        return reply_to_splitted[0].replace("<", "").replace(">", "")

    @api.multi
    def create_smtp_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        sender_instance = sib_api_v3_sdk.SendersApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
        user_sender = sender_instance.get_senders().senders[0]
        smtp_sender = sib_api_v3_sdk.CreateSmtpTemplateSender(email=user_sender.email)
        reply_to = self.format_reply_to(self.reply_to)
        smtp_template = sib_api_v3_sdk.CreateSmtpTemplate(
            sender=smtp_sender,
            template_name=self.name,
            html_content=self.body_html,
            subject=self.name,
            reply_to=reply_to,
            is_active=True,
        )

        try:
            api_response = api_instance.create_smtp_template(smtp_template)
            self.id_sendinblue_tmpl = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling SMTPApi -> create_smtp_template : %s\n" % error_msg)

    @api.multi
    def update_smtp_sendinblue(self, api_instance):
        self.ensure_one()
        reply_to = self.format_reply_to(self.reply_to)
        smtp_template = sib_api_v3_sdk.UpdateSmtpTemplate(
            template_name=self.name,
            html_content=self.body_html,
            subject=self.name,
            reply_to=reply_to,
        )
        try:
            api_instance.update_smtp_template(self.id_sendinblue_tmpl, smtp_template)
        except ApiException as error_msg:
            raise UserError("Exception when calling SMTPApi->update_smtp_template : %s\n" % error_msg)

    @api.multi
    def action_test_mailing(self):
        """
        Override classic test to send a test email from Sendinblue and not Odoo to all the emails from the BAT test list
        of Sendinblue.
        """
        self.ensure_one()
        if self.supplier != 'sendinblue':
            return super(MassMailingProviderSendinblue, self).action_test_mailing()
        configuration = sib_api_v3_sdk.Configuration()
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'sendinblue_api_key'
        )
        configuration.api_key['api-key'] = api_key
        configuration.api_key['partner-key'] = api_key

        api_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(configuration))
        send_test_email = sib_api_v3_sdk.SendTestEmail()
        try:
            api_instance.send_test_template(self.id_sendinblue_tmpl, send_test_email)
        except ApiException as error_msg:
            raise UserError("Exception when calling SMTPApi -> send_test_template : %s\n" % error_msg)

    @api.model
    def _process_mass_mailing_queue(self):
        """
        Override classic cron to send Sendinblue mail via Sendinblue and not Odoo
        """
        mass_mailings = self.search([
            ('state', 'in', ('in_queue', 'sending')),
            '|',
            ('schedule_date', '<', fields.Datetime.now()),
            ('schedule_date', '=', False)
        ])

        # Set Sendinblue API
        configuration = sib_api_v3_sdk.Configuration()
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'sendinblue_api_key'
        )
        configuration.api_key['api-key'] = api_key
        configuration.api_key['partner-key'] = api_key
        api_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(configuration))

        for mass_mailing in mass_mailings:
            user = mass_mailing.write_uid or self.env.user
            mass_mailing = mass_mailing.with_context(**user.sudo(user=user).context_get())

            if len(mass_mailing.get_remaining_recipients()) > 0:
                mass_mailing.state = 'sending'
                if mass_mailing.supplier == 'sendinblue':
                    list_contact_relations = self.env['mail.mass_mailing.list_contact_rel'].search([
                        ('list_id', 'in', mass_mailing.contact_list_ids.ids)
                    ])
                    email_to = [list_contact_rel.contact_id.email for list_contact_rel in list_contact_relations]
                    send_email = sib_api_v3_sdk.SendEmail(email_to=email_to)
                    try:
                        api_instance.send_template(mass_mailing.id_sendinblue_tmpl, send_email)
                    except ApiException as msg_error:
                        raise UserError("Exception when calling SMTPApi -> send_template : %s\n" % msg_error)
                else:
                    mass_mailing.send_mail()
            else:
                mass_mailing.write({'state': 'done', 'sent_date': fields.Datetime.now()})


class MassMailingContactSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    id_sendinblue_contact = fields.Integer("Id contact Sendinblue", readonly=True, copy=False)

    @api.multi
    def create_contact_sendinblue(self, api_instance):
        self.ensure_one()
        create_contact = sib_api_v3_sdk.CreateContact(
            attributes={
                'LASTNAME': self.name,
            },
            email=self.email,
        )
        try:
            api_response = api_instance.create_contact(create_contact)
            self.id_sendinblue_contact = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling ContactsApi -> create_contact : %s\n" % error_msg)

    @api.multi
    def update_contact_sendinblue(self, api_instance):
        self.ensure_one()
        update_contact = sib_api_v3_sdk.UpdateContact({
            'LASTNAME': self.name,
        })
        try:
            api_instance.update_contact(self.email, update_contact)
        except ApiException as error_msg:
            raise UserError("Exception when calling ContactsApi -> update_contact : %s\n" % error_msg)


class MassMailingCampaignSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.campaign'

    id_sendinblue_campaign = fields.Integer("Id campaign Sendinblue", readonly=True, copy=False)
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string="Mail template")

    @api.multi
    def create_campaign_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        campaign_sender = sib_api_v3_sdk.CreateSmtpTemplateSender(email=self.user_id.login)
        # On prend soit le smtp renseigné dans la campagne Odoo, soit le premier smtp de Sendinblue
        template_id = self.mass_mailing_ids and self.mass_mailing_ids[0].id_sendinblue_tmpl or False
        if not template_id:
            smtp_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
            sendinblue_smtps = smtp_instance.get_smtp_templates(template_status='true')
            if not sendinblue_smtps.templates:
                raise UserError("You first need to create a mail template in Sendinblue.")
            template_id = sendinblue_smtps.templates[0].id

        email_campaigns = sib_api_v3_sdk.CreateEmailCampaign(
            sender=campaign_sender,
            name=self.name,
            subject=self.name,
            template_id=template_id
        )

        try:
            api_response = api_instance.create_email_campaign(email_campaigns)
            self.id_sendinblue_campaign = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling EmailCampaignsApi -> create_email_campaign : %s\n" % error_msg)

    @api.multi
    def update_campaign_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        # On prend soit le smtp renseigné dans la campagne Odoo, soit le premier smtp de Sendinblue
        body_html = self.mass_mailing_ids and self.mass_mailing_ids[0].body_html or False
        if not body_html:
            smtp_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
            sendinblue_smtps = smtp_instance.get_smtp_templates(template_status='true', limit=50, offset=0)
            body_html = sendinblue_smtps.templates[0].html_content
        email_campaign = sib_api_v3_sdk.UpdateEmailCampaign(
            name=self.name,
            subject=self.name,
            html_content=body_html
        )

        try:
            api_instance.update_email_campaign(self.id_sendinblue_campaign, email_campaign)
        except ApiException as error_msg:
            raise UserError("Exception when calling EmailCampaignsApi -> update_email_campaign : %s\n" % error_msg)


class MassMailingListSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.list'

    id_sendinblue_list = fields.Integer("Id list Sendinblue", readonly=True, copy=False)
    folder_id = fields.Many2one('mail.mass_mailing.folder', string="Folder")

    @api.multi
    def create_list_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        folder_instance = sib_api_v3_sdk.FoldersApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
        # On prend le premier dossier, s'il n'y en a pas, on en crée un
        folder_id = self.folder_id and self.folder_id.id or False
        if not folder_id:
            try:
                sendinblue_folders = folder_instance.get_folders(limit=10, offset=0)
                folder_id = sendinblue_folders.folders[0].get('id')
            except ValueError:
                new_folder = self.env['mail.mass_mailing.folder'].create({'name': "Dossier %s" % self.name})
                new_folder.create_folder_sendinblue(folder_instance)
                folder_id = new_folder.id_sendinblue_folder

        create_list = sib_api_v3_sdk.CreateList(
            name=self.name,
            folder_id=folder_id
        )

        try:
            api_response = api_instance.create_list(create_list)
            self.id_sendinblue_list = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling ListsApi -> create_list : %s\n" % error_msg)

    @api.multi
    def update_list_sendinblue(self, api_instance):
        self.ensure_one()
        update_list = sib_api_v3_sdk.UpdateList(
            name=self.name
        )

        try:
            api_instance.update_list(self.id_sendinblue_list, update_list)
        except ApiException as error_msg:
            raise UserError("Exception when calling ListsApi -> update_list : %s\n" % error_msg)


class MassMailingFolderSendinblue(models.Model):
    _name = 'mail.mass_mailing.folder'
    _description = "Related to Sendinblue folder's"

    id_sendinblue_folder = fields.Integer("Id folder Sendinblue", readonly=True, copy=False)
    name = fields.Char("Name")
    total_blacklisted = fields.Integer("Blacklisted amount", readonly=True)
    total_subscribers = fields.Integer("Subscribers amount", readonly=True)
    unique_subscribers = fields.Integer("Unique subscribers", readonly=True)

    @api.multi
    def create_folder_sendinblue(self, api_instance):
        self.ensure_one()
        create_folder = sib_api_v3_sdk.CreateUpdateFolder(name=self.name)

        try:
            api_response = api_instance.create_folder(create_folder)
            self.id_sendinblue_folder = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling FoldersApi -> create_folder : %s\n" % error_msg)

    # @api.multi
    # def update_folder_sendinblue(self, api_instance):
    #     self.ensure_one()
    #     update_folder = sib_api_v3_sdk.CreateUpdateFolder(name=self.name)
    #
    #     try:
    #         api_instance.update_folder(self.id_sendinblue_folder, update_folder)
    #     except ApiException as error_msg:
    #         raise UserError("Exception when calling FoldersApi -> update_folder : %s\n" % error_msg)
