# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import json

from urllib import parse
import requests
import pytz

from iso8601 import iso8601
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class OutlookSynchronisationWizard(models.TransientModel):
    _name = 'outlook.sync.wizard'

    synchronise_contacts = fields.Boolean("Synchroniser les contacts", default=False)
    synchronise_calendars = fields.Boolean("Synchroniser les emplois du temps", default=True)

    @api.multi
    def button_do_get_from_outlook(self):
        self.ensure_one()
        if self.synchronise_contacts:
            self.get_contacts_from_outlook()
        if self.synchronise_calendars:
            self.get_calendars_from_outlook()

    @api.multi
    def button_do_send_to_outlook(self):
        self.ensure_one()
        if self.synchronise_contacts:
            self.send_contacts_to_outlook()
        if self.synchronise_calendars:
            self.send_calendars_to_outlook()

    @api.multi
    def get_scope(self):
        self.ensure_one()
        scope = "openid offline_access"
        if self.synchronise_contacts:
            scope += " https://graph.microsoft.com/contacts.readwrite"
        if self.synchronise_calendars:
            scope += " https://graph.microsoft.com/calendars.readwrite"
        return scope

    # CONNECTION TO API OUTLOOK

    @api.multi
    def get_auth_code_outlook(self):
        """
        Demande un code d'autorisation pour l'adresse mail renseignée pour être capable de faire des modifications sur
        Outlook.
        """
        self.ensure_one()
        full_redirect_uri = self.env['ir.config_parameter'].get_param('web.base.url') + u"/outlook_odoo"
        dbname = self.env.cr.dbname
        scope = self.get_scope()

        params = {
            'client_id': "243972aa-f693-41d7-a82b-db2ce249e404",
            'response_type': u"code",
            'redirect_uri': full_redirect_uri,
            'response_mode': "query",
            'scope': scope,
            'state': json.dumps({'d': dbname, 'user_id': self.env.user.id, 'scope': scope}),
        }
        encoded_params = parse.urlencode(params)
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + encoded_params

        return {
            'type': "ir.actions.act_url",
            'url': url,
            'target': "new"}

    @api.model
    def get_refresh_token(self, authorization_code, user_id, scope):
        """
        Permet de récupérer le refresh_token en utilisant l'authorization_code.
        Le refresh_token est spécifique à un utilisateur.
        """
        user = self.env['res.users'].browse(user_id)
        redirect_uri = self.env['ir.config_parameter'].get_param('web.base.url') + u"/outlook_odoo"

        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
        }

        data = {
            'client_id': "243972aa-f693-41d7-a82b-db2ce249e404",
            'scope': scope,
            'code': authorization_code,
            'redirect_uri': redirect_uri,
            'grant_type': "authorization_code",
            'client_secret': "8OxndY0y5/SEEmu=LFK]h0gKZmCI]lGo",
        }

        request_token = requests.post(u"https://login.microsoftonline.com/common/oauth2/v2.0/token",
                                      headers=headers, data=data)
        token_dico = request_token.json()

        user.outlook_refresh_token = token_dico.get('refresh_token')

    @api.multi
    def access_outlook(self):
        """
        Accède à Outlook via la méthode OAuth2.
        """
        session = requests.Session()
        access_token = self.get_token()
        if access_token:
            authorization = u"Bearer " + access_token
        else:
            raise UserError(_(u"Accès refusé, veuillez rafraîchir votre authentification auprès d'Outlook."))

        session.headers.update({
            'Authorization': authorization,
            'accept': u"application/json;",
        })

        return session

    @api.multi
    def get_token(self):
        """
        Permet de récupérer un nouveau token en utilisant le refresh_token lorsque l'access_token n'est plus valide
        (3600s).
        """
        outlook_refresh_token = self.env.user.outlook_refresh_token
        redirect_uri = self.env['ir.config_parameter'].get_param('web.base.url') + u"/outlook_odoo"

        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
        }

        data = {
            'client_id': "243972aa-f693-41d7-a82b-db2ce249e404",
            'scope': self.get_scope(),
            'refresh_token': outlook_refresh_token,
            'redirect_uri': redirect_uri,
            'grant_type': "refresh_token",
            'client_secret': "8OxndY0y5/SEEmu=LFK]h0gKZmCI]lGo",
        }

        request_token = requests.post(u"https://login.microsoftonline.com/common/oauth2/v2.0/token",
                                      headers=headers, data=data)

        token_dico = request_token.json()
        outlook_token = token_dico.get('access_token')

        return outlook_token

    # CONTACTS SYNCHRONISATION

    @api.model
    def odoo_to_outlook_date(self, odoo_date):
        """
        Passe une date du format Odoo au format ISO 8601.
        """
        odoo_datetime = fields.Datetime.from_string(odoo_date)
        tz_info = fields.Datetime.context_timestamp(self, odoo_datetime).tzinfo
        return odoo_datetime.replace(tzinfo=tz_info).astimezone(pytz.UTC).isoformat()

    @api.model
    def outlook_to_odoo_date(self, iso8601_date):
        """
        Passe une date du format ISO 8601 au format Odoo.
        """
        utc_tz_date = iso8601.parse_date(iso8601_date)
        tz_info = fields.Datetime.context_timestamp(self, utc_tz_date.replace(tzinfo=None)).tzinfo
        right_tz_date = utc_tz_date.astimezone(tz_info)
        return fields.Datetime.to_string(right_tz_date.astimezone(tz_info))

    @api.multi
    def get_100_item_infos(self, session, url, sending=False):
        """
        Récupère 100 contacts Outlook. Ne pas oublier de rajouter "?$top=100" à l'url donnée, on ne le fait pas dans la
        fonction car il sera gardé dans '@odata.nextLink'.
        """
        self.ensure_one()
        contacts = session.get(url)
        if contacts.status_code != 200:
            raise UserError(_(u"HTTP Request returned a %d error" % contacts.status_code))
        more_contacts_url = contacts.json().get('@odata.nextLink')

        # Outlook -> Odoo
        if not sending:
            return contacts.json().get('value'), more_contacts_url

        # Odoo -> Outlook
        data_contacts = []
        for contact in contacts.json().get('value'):
            # Ici on garde les lastModifiedDateTime en UTC pour comparer avec les write_date des res.partner car les
            # write_date sont également en UTC dans la base de données.
            utc_write_date = fields.Datetime.to_string(iso8601.parse_date(contact.get('lastModifiedDateTime')))
            data_contacts.append((contact.get('id'), utc_write_date))

        return data_contacts, more_contacts_url

    @api.model
    def get_contact_infos_for_odoo(self, outlook_contact):
        write_date = self.outlook_to_odoo_date(outlook_contact.get('lastModifiedDateTime'))
        email = outlook_contact.get('emailAddresses') and outlook_contact.get('emailAddresses')[0].get('address') or ""
        return {
            'name': outlook_contact.get('displayName'),
            'write_date': write_date,
            'outlook_id': outlook_contact.get('id'),
            'company_id': self.env['res.company'].search([('name', '=', outlook_contact.get('companyName'))]).id,
            'street': outlook_contact.get('businessAddress').get('street'),
            'zip': outlook_contact.get('businessAddress').get('postalCode'),
            'city': outlook_contact.get('businessAddress').get('city'),
            'country_id': self.env['res.country'].search([
                ('name', '=', outlook_contact.get('businessAddress').get('countryOrRegion'))]).id,
            'mobile': outlook_contact.get('mobilePhone'),
            'email': email,
            'comment': outlook_contact.get('personalNotes'),
        }

    @api.multi
    def get_contacts_from_outlook(self):
        """
        Récupère le carnet d'adresse du compte Outlook de l'utilisateur.
        """
        session = self.access_outlook()
        url = "https://graph.microsoft.com/v1.0/me/contacts"
        parameters = "?$select=id,lastModifiedDateTime,displayName,companyName,businessAddress,mobilePhone," \
                     "emailAddresses,personalNotes&$top=100"

        # Récupération des contacts d'Outlook et recherche des contacts à modifier/créer sur Odoo
        outlook_contacts, more_contacts_url = self.get_100_item_infos(session, url + parameters)
        while more_contacts_url:
            more_outlook_contacts, more_contacts_url = self.get_100_item_infos(session, more_contacts_url)
            outlook_contacts += more_outlook_contacts

        for contact in outlook_contacts:
            # Recherche des contacts existants à modifier
            utc_write_date = fields.Datetime.to_string(iso8601.parse_date(contact.get('lastModifiedDateTime')))
            to_update_contact = self.env['res.partner'].search([
                ('outlook_id', '=', contact.get('id')),
                ('write_date', '<', utc_write_date)
            ])
            if to_update_contact:
                contact_infos = self.get_contact_infos_for_odoo(contact)
                to_update_contact.write(contact_infos)
                continue

            # Création de nouveaux contacts depuis Outlook
            if not self.env['res.partner'].search([('outlook_id', '=', contact.get('id'))]):
                contact_infos = self.get_contact_infos_for_odoo(contact)
                self.env['res.partner'].create(contact_infos)

    @api.model
    def update_contact_in_outlook(self, partner, session, url_update):
        write_date = self.odoo_to_outlook_date(partner.write_date)
        contact_infos = {
            'givenName': partner.name,
            'lastModifiedDateTime': write_date,
            'displayName': partner.name,
            'companyName': partner.company_id.name or "",
            'businessAddress': {
                'street': partner.street or "",
                'postalCode': partner.zip or "",
                'city': partner.city or "",
                'countryOrRegion': partner.country_id.name or "",
            },
            'mobilePhone': partner.city or "",
            'emailAddresses': [{
                'address': partner.email or "",
                'name': partner.name or "",
            }],
            'personalNotes': partner.comment or "",
        }
        # On crée le contact sur Outlook

        ans_update = session.patch(url_update, data=json.dumps(contact_infos))
        if ans_update.status_code != 200:
            raise UserError(_(u"HTTP Request returned a %d error" % ans_update.status_code))

    @api.model
    def create_contact_in_outlook(self, partner, session, url_create):
        write_date = self.odoo_to_outlook_date(partner.write_date)
        contact_infos = {
            'givenName': partner.name,
            'lastModifiedDateTime': write_date,
            'displayName': partner.name,
            'companyName': partner.company_id.name or "",
            'businessAddress': {
                'street': partner.street or "",
                'postalCode': partner.zip or "",
                'city': partner.city or "",
                'countryOrRegion': partner.country_id.name or "",
            },
            'mobilePhone': partner.city or "",
            'emailAddresses': [{
                'address': partner.email or "",
                'name': partner.name or "",
            }],
            'personalNotes': partner.comment or "",
        }
        # On crée le contact sur Outlook
        ans_create = session.post(url_create, data=json.dumps(contact_infos))
        if ans_create.status_code != 201:
            raise UserError(_(u"HTTP Request returned a %d error" % ans_create.status_code))
        # L'id Outlook d'un contact est attribué à sa création dans Outlook (impossible de lui donner un autre
        # id car il sera écrasé). On transfert cet id au contact Odoo qui n'en avait pas encore.
        partner.outlook_id = ans_create.json().get('id')

    @api.model
    def delete_item_in_outlook(self, session, url_delete):
        """
        L'utilisateur doit supprimer les contacts/évènements via Odoo, sinon il reviendra lors du prochain export de
        Odoo vers Outlook.
        """
        ans_delete = session.delete(url_delete)
        if ans_delete.status_code != 204:
            raise UserError(_(u"HTTP Request returned a %d error" % ans_delete.status_code))

    @api.multi
    def send_contacts_to_outlook(self):
        """
        Envoi les contacts vers le compte Outlook de l'utilisateur courant.
        """
        self.ensure_one()
        session = self.access_outlook()
        session.headers.update({
            'Content-Type': u"application/json;",
        })
        url_create = "https://graph.microsoft.com/v1.0/me/contacts"
        parameters = "?$select=id,lastModifiedDateTime&$top=100"

        # Récupération des contacts d'Outlook et recherche des contacts à créer/modifier sur Outlook
        data_contacts, more_contacts_url = self.get_100_item_infos(session, url_create + parameters, sending=True)
        while more_contacts_url:
            more_data_contacts, more_contacts_url = self.get_100_item_infos(session, more_contacts_url, sending=True)
            data_contacts += more_data_contacts
        outlook_ids = []
        updated_contacts = self.env['res.partner']
        deleted_contact_outlook_ids = []
        for data_contact in data_contacts:
            # Les contacts Outlook non liés à des res.partner doivent être supprimés lors de l'export Odoo -> Outlook
            if not self.env['res.partner'].search([('outlook_id', '=', data_contact[0])]):
                deleted_contact_outlook_ids.append(data_contact[0])
            else:
                outlook_ids.append(data_contact[0])
                updated_contacts |= self.env['res.partner'].search([
                    ('outlook_id', '=', data_contact[0]),
                    ('write_date', '>', data_contact[1])
                ])
        new_contacts = self.env['res.partner'].search([('outlook_id', 'not in', outlook_ids)])

        # Mise à jour des contacts modifiés dans Odoo
        for updated_contact in updated_contacts:
            url_update = url_create + "/%s" % updated_contact.outlook_id
            self.update_contact_in_outlook(updated_contact, session, url_update)

        # Création de nouveaux contacts dans Outlook
        for new_contact in new_contacts:
            self.create_contact_in_outlook(new_contact, session, url_create)

        # Suppression des contacts obsolètes dans Outlook
        for deleted_contact_outlook_id in deleted_contact_outlook_ids:
            url_delete = url_create + "/%s" % deleted_contact_outlook_id
            self.delete_item_in_outlook(session, url_delete)

    # CALENDARS SYNCHRONISATION

    @api.model
    def get_event_infos_for_odoo(self, outlook_event, user_id):
        # Attention : Il faut récupérer les plages horaires sur le fuseau UTC, car Odoo rajoute 2h par rapport à ce
        # qu'il enregistre en base. SAUF pour la write_date (Pourquoi?)
        write_date = self.outlook_to_odoo_date(outlook_event.get('lastModifiedDateTime'))
        start_date = fields.Datetime.to_string(iso8601.parse_date(outlook_event.get('start').get('dateTime')))
        end_date = fields.Datetime.to_string(iso8601.parse_date(outlook_event.get('end').get('dateTime')))
        show_as = 'free' if outlook_event.get('showAs') == "free" else 'busy'
        location = outlook_event.get('location') and outlook_event.get('location').get('displayName') or ""
        return {
            'name': outlook_event.get('subject'),
            'write_date': write_date,
            'outlook_id': outlook_event.get('id'),
            'user_id': user_id,
            'start': start_date,
            'stop': end_date,
            'description': outlook_event.get('bodyPreview'),
            'location': location,
            'show_as': show_as,
        }

    @api.multi
    def get_calendars_from_outlook(self):
        """
        Récupère l'emploi du temps du compte Outlook de l'utilisateur.
        """
        session = self.access_outlook()
        url = "https://graph.microsoft.com/v1.0/me/events"
        parameters = "?$select=subject,id,start,end,bodyPreview,showAs,lastModifiedDateTime&$top=100"

        # Récupération des évènements d'Outlook et recherche des évènements à modifer/créer sur Odoo
        outlook_events, more_event_url = self.get_100_item_infos(session, url + parameters)
        while more_event_url:
            more_outlook_events, more_event_url = self.get_100_item_infos(session, more_event_url)
            outlook_events += more_outlook_events

        user_id = self.env.user.id
        for event in outlook_events:
            # Recherche des évènements existants à modifier
            utc_write_date = fields.Datetime.to_string(iso8601.parse_date(event.get('lastModifiedDateTime')))
            to_update_event = self.env['calendar.event'].search([
                ('outlook_id', '=', event.get('id')),
                ('write_date', '<', utc_write_date),
            ])
            if to_update_event:
                event_infos = self.get_event_infos_for_odoo(event, user_id)
                to_update_event.write(event_infos)
                continue

            # Création de nouveaux évènements depuis Outlook
            if not self.env['calendar.event'].search([('outlook_id', '=', event.get('id'))]):
                event_infos = self.get_event_infos_for_odoo(event, user_id)
                self.env['calendar.event'].create(event_infos)

    @api.model
    def get_event_infos_for_outlook(self, calendar_event):
        write_date = self.odoo_to_outlook_date(calendar_event.write_date)
        start_date = self.odoo_to_outlook_date(calendar_event.start)
        start_dt = fields.Datetime.from_string(calendar_event.start)
        start_tz = fields.Datetime.context_timestamp(self, start_dt).tzinfo.zone
        end_date = self.odoo_to_outlook_date(calendar_event.stop)
        end_dt = fields.Datetime.from_string(calendar_event.stop)
        end_tz = fields.Datetime.context_timestamp(self, end_dt).tzinfo.zone
        show_as = "free" if calendar_event.show_as == 'free' else "busy"
        return {
            'subject': calendar_event.name or "",
            'lastModifiedDateTime': write_date or "",
            'start': {
                'dateTime': start_date or "",
                'timeZone': start_tz or "",
            },
            'end': {
                'dateTime': end_date or "",
                'timeZone': end_tz or "",
            },
            'bodyPreview': calendar_event.description or "",
            'location': {
                'displayName': calendar_event.location or "",
            },
            # 'show_as': show_as,
        }

    @api.model
    def update_calendars_in_outlook(self, calendar_event, session, url_update):
        event_infos = self.get_event_infos_for_outlook(calendar_event)
        # On met à jour l'évènement sur Outlook
        ans_update = session.patch(url_update, data=json.dumps(event_infos))
        if ans_update.status_code != 200:
            raise UserError(_(u"HTTP Request returned a %d error" % ans_update.status_code))

    @api.model
    def create_calendars_in_outlook(self, calendar_event, session, url_create):
        event_infos = self.get_event_infos_for_outlook(calendar_event)
        # On crée un nouvel évènement sur Outlook
        ans_create = session.post(url_create, data=json.dumps(event_infos))
        if ans_create.status_code != 201:
            raise UserError(_(u"HTTP Request returned a %d error" % ans_create.status_code))
        # L'id Outlook d'un évènement est attribué à sa création dans Outlook (impossible de lui donner un autre
        # id car il sera écrasé). On transfert cet id à l'évènement Odoo qui n'en avait pas encore.
        calendar_event.outlook_id = ans_create.json().get('id')

    def send_calendars_to_outlook(self):
        """
        Envoi l'emploi du temps de l'utilisateur courant sur son compte Outlook.
        """
        self.ensure_one()
        session = self.access_outlook()
        session.headers.update({
            'Content-Type': u"application/json;",
        })
        url_create = "https://graph.microsoft.com/v1.0/me/events"
        parameters = "?$select=id,lastModifiedDateTime&$top=1"

        # Récupération des évènements d'Outlook et recherche des évènements à créer/modifier sur Outlook
        data_events, more_events_url = self.get_100_item_infos(session, url_create + parameters, sending=True)
        while more_events_url:
            more_data_events, more_events_url = self.get_100_item_infos(session, more_events_url, sending=True)
            data_events += more_data_events
        outlook_ids = []
        updated_events = self.env['calendar.event']
        deleted_event_outlook_ids = []
        for data_event in data_events:
            # Les évènements Outlook non liés à des calendar.event doivent être supprimés lors de l'export
            # Odoo -> Outlook
            # if not self.env['calendar.event'].search([('outlook_id', '=', data_contact[0])]):
            #     deleted_event_outlook_ids.append(data_contact[0])
            # else:
            outlook_ids.append(data_event[0])
            updated_events |= self.env['calendar.event'].search([
                ('outlook_id', '=', data_event[0]),
                ('write_date', '>', data_event[1])
            ])
        new_events = self.env['calendar.event'].search([('outlook_id', 'not in', outlook_ids)])

        # Mise à jour des contacts modifiés dans Odoo
        for updated_event in updated_events:
            url_update = url_create + "/%s" % updated_event.outlook_id
            self.update_calendars_in_outlook(updated_event, session, url_update)

        # # Création de nouveaux contacts dans Outlook
        # for new_event in new_events:
        #     self.create_calendars_in_outlook(new_event, session, url_create)
        #
        # # Suppression des contacts obsolètes dans Outlook
        # for deleted_event_outlook_id in deleted_event_outlook_ids:
        #     url_delete = url_create + "/%s" % deleted_event_outlook_id
        #     self.delete_item_in_outlook(session, url_delete)


class ResUsersOutlook(models.Model):
    _inherit = 'res.users'

    outlook_refresh_token = fields.Char("Refresh token")


class OuestacroResPartnerOutlook(models.Model):
    _inherit = 'res.partner'

    outlook_id = fields.Char("Identifiant Outlook")


class OuestacroCalendarEventOutlook(models.Model):
    _inherit = 'calendar.event'

    outlook_id = fields.Char("Identifiant Outlook")
