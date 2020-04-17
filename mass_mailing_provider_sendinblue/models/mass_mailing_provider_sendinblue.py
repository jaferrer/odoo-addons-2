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

import dateutil
import pytz
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from odoo.exceptions import UserError
from odoo import fields, models, api


class MassMailingProviderSendinblue(models.Model):
    _inherit = 'mail.mass_mailing'

    supplier = fields.Selection(selection_add=[('sendinblue', "Sendinblue")])
    id_sendinblue_tmpl = fields.Integer("Id mail template Sendinblue", readonly=True)
    write_date_sendinblue = fields.Datetime("Last modification date Sendinblue", readonly=True)

    @api.multi
    def write(self, vals):
        """
        La date de modification Outlook est une date de modification qui peut-être imposée.
        """
        res = super(MassMailingProviderSendinblue, self).write(vals)

        if not vals.get('write_date_sendinblue') and not self.env.context.get('creation'):
            for rec in self:
                rec.write_date_sendinblue = rec.write_date

        return res

    @api.multi
    def create_smtp_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        sender_instance = sib_api_v3_sdk.SendersApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
        user_sender = sender_instance.get_senders().senders[0]
        smtp_sender = sib_api_v3_sdk.CreateSmtpTemplateSender(email=user_sender.email)
        smtp_template = sib_api_v3_sdk.CreateSmtpTemplate(
            sender=smtp_sender,
            template_name=self.name,
            html_content=self.body_html,
            subject=self.name,
            is_active=True
        )

        try:
            api_response = api_instance.create_smtp_template(smtp_template)
            self.id_sendinblue_tmpl = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling SMTPApi -> create_smtp_template : %s\n" % error_msg)

    @api.multi
    def update_smtp_sendinblue(self, api_instance):
        self.ensure_one()
        smtp_template = sib_api_v3_sdk.UpdateSmtpTemplate(
            template_name=self.name,
            html_content=self.body_html,
            subject=self.name,
        )
        try:
            api_instance.update_smtp_template(self.id_sendinblue_tmpl, smtp_template)
            self.write_date_sendinblue = fields.Datetime.to_string(fields.Datetime.now())
        except ApiException as error_msg:
            raise UserError("Exception when calling SMTPApi->update_smtp_template : %s\n" % error_msg)

    @api.multi
    def update_smtp_odoo(self, sendinblue_smtp_info, sendinblue_write_date):
        self.ensure_one()
        self.write({
            'name': sendinblue_smtp_info.subject,
            'body_html': sendinblue_smtp_info.html_content,
            'sendinblue_write_date': sendinblue_write_date,
        })


class MassMailingContactSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    id_sendinblue_contact = fields.Integer("Id contact Sendinblue", readonly=True, copy=False)
    write_date_sendinblue = fields.Datetime("Last modification date Sendinblue", readonly=True)

    @api.multi
    def write(self, vals):
        """
        La date de modification Outlook est une date de modification qui peut-être imposée.
        """
        res = super(MassMailingContactSendinblue, self).write(vals)

        if not vals.get('write_date_sendinblue') and not self.env.context.get('creation'):
            for rec in self:
                rec.write_date_sendinblue = rec.write_date

        return res

    @api.multi
    def create_contact_sendinblue(self, api_instance):
        self.ensure_one()
        self.write_date_sendinblue = self.write_date
        correct_date = self.env.user.localize_date(self.write_date_sendinblue)
        create_contact = sib_api_v3_sdk.CreateContact(
            attributes={
                'TITLE': self.title_id.name,
                'LASTNAME': self.name,
                'COMPANY_NAME': self.company_name,
                'COUNTRY': self.country_id.name,
                'WRITE_DATE_SENDINBLUE': correct_date,
                'ODOO_CONTACT_ID': self.id,
            },
            email=self.email,
        )
        try:
            api_response = api_instance.create_contact(create_contact)
            self.id_sendinblue_contact = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling ContactsApi -> create_contact : %s\n" % error_msg)

    @api.multi
    def update_contact_sendinblue(self, api_instance, odoo_correct_date):
        self.ensure_one()
        update_contact = sib_api_v3_sdk.UpdateContact({
            'TITLE': self.title_id.name,
            'LASTNAME': self.name,
            'COMPANY_NAME': self.company_name,
            'COUNTRY': self.country_id.name,
            'WRITE_DATE_SENDINBLUE': odoo_correct_date,
            'ODOO_CONTACT_ID': self.id,
        })
        try:
            api_instance.update_contact(self.email, update_contact)
        except ApiException as error_msg:
            raise UserError("Exception when calling ContactsApi -> update_contact : %s\n" % error_msg)

    @api.multi
    def update_contact_odoo(self, sendinblue_contact_info, sendinblue_write_date_dt):
        self.ensure_one()
        title = self.env['res.partner.title'].search([
            ('name', '=', sendinblue_contact_info.attributes.get('TITLE'))
        ])
        country = self.env['res.country'].search([
            ('name', '=', sendinblue_contact_info.attributes.get('COUNTRY_NAME'))
        ])
        self.write({
            'name': sendinblue_contact_info.attributes.get('LASTNAME'),
            'title_id': title.id,
            'company_name': sendinblue_contact_info.attributes.get('COMPANY_NAME'),
            'country_id': country.id,
            'write_date_sendinblue': fields.Datetime.to_string(sendinblue_write_date_dt),
        })

    @api.model
    def create_contact_odoo(self, api_instance, sendinblue_contact):
        title = self.env['res.partner.title'].search([
            ('name', '=', sendinblue_contact.get('attributes').get('TITLE'))
        ])
        country = self.env['res.country'].search([
            ('name', '=', sendinblue_contact.get('attributes').get('COUNTRY'))
        ])
        last_write_dt = dateutil.parser.parse(sendinblue_contact.get('modifiedAt'))
        last_write_dt = last_write_dt.replace(
            tzinfo=last_write_dt.tzinfo).astimezone(pytz.UTC).replace(tzinfo=None)
        odoo_contact = self.create({
            'name': sendinblue_contact.get('attributes').get('LASTNAME'),
            'email': sendinblue_contact.get('email'),
            'title_id': title.id,
            'company_name': sendinblue_contact.get('attributes').get('COMPANY_NAME'),
            'country_id': country.id,
            'write_date_sendinblue': fields.Datetime.to_string(last_write_dt),
            'id_sendinblue_contact': sendinblue_contact.get('id')
        })

        update_contact = sib_api_v3_sdk.UpdateContact({
            'ODOO_CONTACT_ID': odoo_contact.id,
        })
        api_instance.update_contact(sendinblue_contact.get('email'), update_contact)


class MassMailingCampaignSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.campaign'

    id_sendinblue_campaign = fields.Integer("Id campaign Sendinblue", readonly=True, copy=False)
    write_date_sendinblue = fields.Datetime("Last modification date Sendinblue", readonly=True)

    @api.multi
    def write(self, vals):
        """
        La date de modification Outlook est une date de modification qui peut-être imposée.
        """
        res = super(MassMailingCampaignSendinblue, self).write(vals)

        if not vals.get('write_date_sendinblue') and not self.env.context.get('creation'):
            for rec in self:
                rec.write_date_sendinblue = rec.write_date

        return res

    @api.multi
    def create_campaign_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        campaign_sender = sib_api_v3_sdk.CreateSmtpTemplateSender(email=self.user_id.login)
        # On prend soit le smtp renseigné dans la campagne Odoo, soit le premier smtp de Sendinblue
        template_id = self.mass_mailing_ids and self.mass_mailing_ids[0].id_sendinblue_tmpl or False
        if not template_id:
            smtp_instance = sib_api_v3_sdk.SMTPApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
            sendinblue_smtps = smtp_instance.get_smtp_templates(template_status='true', limit=50, offset=0)
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
        body_html = self.mass_mailing_ids[0].body_html
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
            self.write_date_sendinblue = fields.Datetime.to_string(fields.Datetime.now())
        except ApiException as error_msg:
            raise UserError("Exception when calling EmailCampaignsApi -> update_email_campaign : %s\n" % error_msg)

    @api.multi
    def update_campaign_odoo(self, sendinblue_campaign_info, sendinblue_write_date):
        self.ensure_one()
        self.write({
            'name': sendinblue_campaign_info.get('name'),
            'sendinblue_write_date': sendinblue_write_date,
        })


class MassMailingListSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.list'

    id_sendinblue_list = fields.Integer("Id list Sendinblue", readonly=True, copy=False)

    @api.multi
    def write(self, vals):
        """
        La date de modification Outlook est une date de modification qui peut-être imposée.
        """
        res = super(MassMailingListSendinblue, self).write(vals)

        if not vals.get('write_date_sendinblue') and not self.env.context.get('creation'):
            for rec in self:
                rec.write_date_sendinblue = rec.write_date

        return res

    @api.multi
    def create_list_sendinblue(self, api_instance, wizard):
        self.ensure_one()
        folder_instance = sib_api_v3_sdk.FoldersApi(sib_api_v3_sdk.ApiClient(wizard.get_sendinblue_api_configuration()))
        # On prend le premier dossier, s'il n'y en a pas, on en crée un
        try:
            sendinblue_folders = folder_instance.get_folders(limit=10, offset=0)
            folder_id = sendinblue_folders.folders[0].get('id')
        except ValueError:
            new_tag = self.env['mail.mass_mailing.tag'].create({'name': "Dossier %s" % self.name})
            new_tag.create_tag_sendinblue(folder_instance)
            folder_id = new_tag.id_sendinblue_folder

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
            self.write_date_sendinblue = fields.Datetime.to_string(fields.Datetime.now())
        except ApiException as error_msg:
            raise UserError("Exception when calling ListsApi -> update_list : %s\n" % error_msg)


class MassMailingTagSendinblue(models.Model):
    _inherit = 'mail.mass_mailing.tag'

    id_sendinblue_folder = fields.Integer("Id folder Sendinblue", readonly=True, copy=False)

    @api.multi
    def write(self, vals):
        """
        La date de modification Outlook est une date de modification qui peut-être imposée.
        """
        res = super(MassMailingTagSendinblue, self).write(vals)

        if not vals.get('write_date_sendinblue') and not self.env.context.get('creation'):
            for rec in self:
                rec.write_date_sendinblue = rec.write_date

        return res

    @api.multi
    def create_tag_sendinblue(self, api_instance):
        self.ensure_one()
        create_folder = sib_api_v3_sdk.CreateUpdateFolder(name=self.name)

        try:
            api_response = api_instance.create_folder(create_folder)
            self.id_sendinblue_folder = api_response.id
        except ApiException as error_msg:
            raise UserError("Exception when calling FoldersApi -> create_folder : %s\n" % error_msg)

    @api.multi
    def update_tag_sendinblue(self, api_instance):
        self.ensure_one()
        update_folder = sib_api_v3_sdk.CreateUpdateFolder(name=self.name)

        try:
            api_instance.update_folder(self.id_sendinblue_folder, update_folder)
        except ApiException as error_msg:
            raise UserError("Exception when calling FoldersApi -> update_folder : %s\n" % error_msg)
