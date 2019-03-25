# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import logging
import json
import urllib2
# import datetime
from datetime import timedelta, datetime
import werkzeug
import gdata.contacts.client
import gdata.contacts.data
import gdata.data
import gdata.gauth

from odoo import api, fields, models, _
from odoo.addons.google_account import TIMEOUT
from odoo.tools import exception_to_unicode
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


def status_response(status):
    return int(str(status)[0]) == 2


class LmdtGoogleContacts(models.Model):
    STR_SERVICE = 'contacts'
    _name = 'google.%s' % STR_SERVICE
    _description = "Contacts Google"

    @api.model
    def _default_google_uri(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        redirect_uri = base_url + "/google_account/authentication"
        uri = self._get_google_token_uri(
            scope=self.get_google_scope(),
            redirect_uri=redirect_uri)
        return uri

    @api.model
    def _default_access_token_generated(self):
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        return False if not current_user.google_contacts_token else True

    google_uri = fields.Char(u"Génération URI", default=_default_google_uri)
    access_token_present = fields.Boolean(u"Présence d'un access token", default=_default_access_token_generated)

    def get_last_sync_date(self):
        """
            Retourne la date de la dernière synchronisation des contacts
        """
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        sync_date = fields.Datetime.from_string(current_user.google_contacts_last_sync_date) + timedelta(minutes=0)
        return current_user.google_contacts_last_sync_date and sync_date or False

    def synchronize_contacts_cron(self):
        """
            Synchronisation automatique des contacts pour chaque utilisateur ayant coché cette option et ayant déjà
            effectué une synchronisation manuelle
        """
        users = self.env['res.users'].search([
            ('google_contacts_last_sync_date', '!=', False),
            ('contact_synchronization', '=', True)])

        _logger.info(u"Synchronisation des contacts - Début par cron")

        for user_to_sync in users.ids:
            _logger.info(u"Synchronisation des contacts - Début de la synchronisation pour un nouvel "
                         u"utilisateur [%s]", user_to_sync)
            try:
                self.sudo(user_to_sync).synchronize_contacts(True)
            except ValidationError as e:
                _logger.info(u"[%s] Synchronisation des contacts - Exception : %s !", user_to_sync,
                             exception_to_unicode(e))
        _logger.info(u"Synchronisation des contacts - Fin par cron")

    def synchronize_contacts(self, last_sync=True):
        """
            Synchronisation manuelle des contacts pour l'utilisateur en cours
        """
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)

        recs = self.sudo(user_to_sync)

        if not current_user.google_contacts_token:
            raise UserError(u"Attention, aucun code d'accès n'a été généré pour l'utilisateur %s. Veuillez effectuer "
                            u"cette première étape avant de lancer toute synchronisation." % current_user.name)

        if not current_user.contact_synchronization:
            raise UserError(u"La synchronisation des contacts vers Google n'a pas été activée pour l'utilisateur %s"
                            % current_user.name)
        else:
            if not current_user.google_contacts_token_validity or \
                    fields.Datetime.from_string(current_user.google_contacts_token_validity) < (
                    datetime.now() + timedelta(minutes=1)):
                recs.do_refresh_token()
                current_user.refresh()

            if last_sync and recs.env.user.google_contacts_last_sync_date:
                last_sync = recs.env.user.google_contacts_last_sync_date
                _logger.info(u"[%s] Synchronisation des contacts - Dernière synchronisation : %s !",
                             user_to_sync, last_sync)
            else:
                last_sync = False
                _logger.info(u"[%s] Synchronisation des contacts - Synchronisation complète", user_to_sync)

            recs.update_contacts_from_google(last_sync)
            recs.create_new_contacts_or_update_from_odoo(last_sync)
            recs.delete_contacts()
            current_user.sudo().write({'google_contacts_last_sync_date': datetime.now()})

    def update_contacts_from_google(self, last_sync):
        """
            MAJ des contacts Odoo modifiés dans Google depuis la dernière synchronisation
        """
        client_id = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_id')
        client_secret = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_secret')
        scope = self.get_google_scope()
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        access_token = current_user.google_contacts_token
        gd_client = gdata.contacts.client.ContactsClient()
        gd_client.auth_token = gdata.gauth.OAuth2Token(client_id, client_secret, scope, '', access_token=access_token)

        if not last_sync:
            # 1ère synchronisation : aucun contact n'a encore été importé d'Odoo
            pass
        else:
            # MAJ dans Odoo des contacts modifiés dans Google depuis la dernière synchronisation
            updated_min = last_sync[0: 10] + 'T' + last_sync[11: 19]
            query = gdata.contacts.client.ContactsQuery()
            query.max_results = '10000'
            query.updated_min = updated_min
            contacts_google = gd_client.GetContacts(q=query)

            for contact in contacts_google.entry:
                partner = self.env['res.partner'].search([('google_contacts_id', '=', contact.id.text)])

                if not partner:
                    # Le contact n'est pas dans Odoo: pas de mise à jour
                    pass
                else:
                    email = ({c.rel: c for c in contact.email}.get(gdata.data.WORK_REL, '') or
                             [c for c in contact.email][0]) if contact.email else ''

                    phone, phone2, mobile = [''] * 3
                    if contact.phone_number:
                        phone = {c.rel: c for c in contact.phone_number}.get(gdata.data.MAIN_REL, '')
                        phone2 = {c.rel: c for c in contact.phone_number}.get(gdata.data.OTHER_REL, '')
                        mobile = {c.rel: c for c in contact.phone_number}.get(gdata.data.MOBILE_REL, '')

                    address = False
                    if contact.structured_postal_address:
                        add = contact.structured_postal_address
                        address = ({c.rel: c for c in add}.get(gdata.data.WORK_REL, '') or [c for c in add][0]) if \
                            contact.structured_postal_address else False

                    partner.sudo().write({
                        'name': contact.name.full_name.text,
                        'email': email.address if email != '' else '',
                        'phone': phone.text if phone != '' else '',
                        'phone2': phone2.text if phone2 != '' else '',
                        'mobile': mobile.text if mobile != '' else '',
                        'street': address.street.text if address and address.street else '',
                        'street2': address.neighborhood.text if address and address.neighborhood else '',
                        'city': address.city.text if address and address.city else '',
                        'zip': address.postcode.text if address and address.postcode else '',
                        'zip_id': '',
                        'country_id': self.env['res.country'].search([('code', '=', address.country.text)]).id
                        if address and address.country else '',
                    })

    def create_new_contacts_or_update_from_odoo(self, last_sync):
        """
            MAJ des contacts Google modifiés dans Odoo depuis la dernière synchronisation
        """
        if not last_sync:
            # 1ère synchronisation : j'intègre tous les contacts Odoo dans Google
            partners = self.env['res.partner'].search([])
        else:
            # j'intègre dans Google uniquement les contacts ajoutés/modifiés depuis la dernière synchronisation
            partners = self.env['res.partner'].search([('write_date', '>=', last_sync)])

        client_id = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_id')
        client_secret = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_secret')
        scope = self.get_google_scope()
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        access_token = current_user.google_contacts_token
        create_route = 'https://www.google.com/m8/feeds/contacts/default/full'
        gd_client = gdata.contacts.client.ContactsClient()
        gd_client.auth_token = gdata.gauth.OAuth2Token(client_id, client_secret, scope, '', access_token=access_token)

        # Recherche du groupe
        groupes = gd_client.GetGroups()
        for groupe in groupes.entry:
            if groupe.system_group and groupe.system_group.id == 'Contacts':
                group_href = groupe.id.text

        for partner in partners:
            if not partner.google_contacts_id:
                # Le contact n'est pas encore dans Google => création
                new_contact = self.create_contact(partner, group_href)
                contact_entry = gd_client.CreateContact(new_contact, insert_uri=create_route)
                partner.sudo().write({'google_contacts_id': contact_entry.id.text})
            else:
                # Le contact est déjà présent dans Google => MAJ
                contact = self.update_contact(partner)
                try:
                    gd_client.Update(contact)
                except gdata.client.RequestError, e:
                    if e.status == 412:
                        # Etags mismatch: handle the exception.
                        pass

    def create_contact(self, partner, group_href):
        """
            Création d'un contact dans Google à partir des données renseignées dans le res.partner
        """
        data = self.partner_infos(partner)

        new_contact = gdata.contacts.data.ContactEntry()

        # Nom du contact
        new_contact.name = gdata.data.Name(full_name=gdata.data.FullName(text=data['FullName']))

        # Adresse mail
        new_contact.email.append(gdata.data.Email(address=data['Email'], primary='true', rel=gdata.data.WORK_REL))

        # Téléphones
        new_contact.phone_number.append(gdata.data.PhoneNumber(text=data['Phone'],
                                                               rel=gdata.data.MAIN_REL, primary='true'))
        new_contact.phone_number.append(gdata.data.PhoneNumber(text=data['Phone2'],
                                                               rel=gdata.data.OTHER_REL))
        new_contact.phone_number.append(gdata.data.PhoneNumber(text=data['Mobile'],
                                                               rel=gdata.data.MOBILE_REL))

        # Adresse postale
        street2 = '\n' + data['Street2'] if data['Street2'] != '' else ''
        postcode = '\n' + data['Postcode'] if data['Postcode'] != '' else ''
        city = ' ' + data['City'] if data['City'] != '' else ''
        region = ', ' + data['Region'] if data['Region'] != '' else ''
        country = '\n' + data['Country'] if data['Country'] != '' else ''
        formatted_address = data['Street'] + street2 + postcode + city + region + country

        new_contact.structured_postal_address.append(gdata.data.StructuredPostalAddress(
            rel=gdata.data.WORK_REL, primary='true',
            street=gdata.data.Street(text=data['Street']),
            neighborhood=gdata.data.Neighborhood(text=data['Street2']),
            city=gdata.data.City(text=data['City']),
            region=gdata.data.Region(text=data['Region']),
            postcode=gdata.data.Postcode(text=data['Postcode']),
            country=gdata.data.Country(text=data['Country']),
            formattedAddress=gdata.data.FormattedAddress(text=formatted_address)
        ))

        # Mise à jour du groupe
        new_contact.group_membership_info.append(gdata.contacts.data.GroupMembershipInfo(href=group_href))

        return new_contact

    def update_contact(self, partner):
        """
            MAJ d'un contact dans Google à partir des données renseignées dans le res.partner
        """
        client_id = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_id')
        client_secret = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_secret')
        scope = self.get_google_scope()
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        access_token = current_user.google_contacts_token
        gd_client = gdata.contacts.client.ContactsClient()
        gd_client.auth_token = gdata.gauth.OAuth2Token(client_id, client_secret, scope, '', access_token=access_token)
        contact = gd_client.GetContact(partner.google_contacts_id)

        data = self.partner_infos(partner)

        # Nom du contact
        contact.name.full_name.text = data['FullName']

        # Liste des numéros de téléphone existants
        liste_tel = []
        for phone in contact.phone_number:
            liste_tel.append(phone.rel)

        # Mise à jour des numéros existants
        for phone in contact.phone_number:
            if phone.rel == gdata.data.MAIN_REL:
                phone.text = data['Phone']
            if phone.rel == gdata.data.OTHER_REL:
                phone.text = data['Phone2']
            if phone.rel == gdata.data.MOBILE_REL:
                phone.text = data['Mobile']

        # Ajout des nouveaux numéros
        if gdata.data.MAIN_REL not in liste_tel:
            contact.phone_number.append(gdata.data.PhoneNumber(text=data['Phone'],
                                                               rel=gdata.data.MAIN_REL, primary='true'))
        if gdata.data.OTHER_REL not in liste_tel:
            contact.phone_number.append(gdata.data.PhoneNumber(text=data['Phone2'], rel=gdata.data.OTHER_REL))
        if gdata.data.MOBILE_REL not in liste_tel:
            contact.phone_number.append(gdata.data.PhoneNumber(text=data['Mobile'], rel=gdata.data.MOBILE_REL))

        # Liste des email existants
        liste_email = []
        adr_pro = False
        for email in contact.email:
            liste_email.append(email.rel)
            if email.label == 'Professionnel':
                adr_pro = True

        # Mise à jour des email existants
        for email in contact.email:
            if email.rel == gdata.data.WORK_REL or email.label == 'Professionnel':
                email.address = data['Email']

        # Ajout des nouveaux email
        if gdata.data.WORK_REL not in liste_email and not adr_pro:
            contact.email.append(gdata.data.Email(address=data['Email'], rel=gdata.data.WORK_REL))

        # Liste des adresses existantes
        liste_adresses = []
        adr_pro = False
        for adresse in contact.structured_postal_address:
            liste_adresses.append(adresse.rel)
            if adresse.label == 'Professionnel':
                adr_pro = True

        street2 = '\n' + data['Street2'] if data['Street2'] != '' else ''
        postcode = '\n' + data['Postcode'] if data['Postcode'] != '' else ''
        city = ' ' + data['City'] if data['City'] != '' else ''
        region = ', ' + data['Region'] if data['Region'] != '' else ''
        country = '\n' + data['Country'] if data['Country'] != '' else ''
        formatted_address = data['Street'] + street2 + postcode + city + region + country

        # Mise à jour des adresses existantes
        for adresse in contact.structured_postal_address:
            if adresse.rel == gdata.data.WORK_REL or adresse.label == 'Professionnel':
                if adresse.street:
                    adresse.street.text = data['Street']
                if adresse.neighborhood:
                    adresse.neighborhood.text = data['Street2']
                if adresse.city:
                    adresse.city.text = data['City']
                if adresse.region:
                    adresse.region.text = data['Region']
                if adresse.postcode:
                    adresse.postcode.text = data['Postcode']
                if adresse.country:
                    adresse.country.text = data['Country']
                if adresse.formatted_address:
                    adresse.formatted_address.text = formatted_address

        # Ajout des nouvelles adresses
        if gdata.data.WORK_REL not in liste_adresses and not adr_pro:
            contact.structured_postal_address.append(gdata.data.StructuredPostalAddress(
                rel=gdata.data.WORK_REL,
                street=gdata.data.Street(text=data['Street']),
                neighborhood=gdata.data.Neighborhood(text=data['Street2']),
                city=gdata.data.City(text=data['City']),
                region=gdata.data.Region(text=data['Region']),
                postcode=gdata.data.Postcode(text=data['Postcode']),
                country=gdata.data.Country(text=data['Country']),
                formattedAddress=gdata.data.FormattedAddress(text=formatted_address)
            ))

        return contact

    def delete_contacts(self):
        """
            Suppression dans Google des contacts archivés dans Odoo
        """
        client_id = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_id')
        client_secret = self.env['ir.config_parameter'].sudo().get_param('google_contacts_client_secret')
        scope = self.get_google_scope()
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        access_token = current_user.google_contacts_token
        gd_client = gdata.contacts.client.ContactsClient()
        gd_client.auth_token = gdata.gauth.OAuth2Token(client_id, client_secret, scope, '', access_token=access_token)

        query = gdata.contacts.client.ContactsQuery()
        query.max_results = '10000'
        contacts_google = gd_client.GetContacts(q=query)
        list_google_contacts_id_archive = []
        partners = self.env['res.partner'].search([('active', '=', False)])

        for partner in partners:
            list_google_contacts_id_archive.append(partner.google_contacts_id)

        for contact in contacts_google.entry:
            if contact.id.text in list_google_contacts_id_archive:
                # Contact archivé => à supprimer de google
                try:
                    gd_client.Delete(contact)
                except gdata.client.RequestError, e:
                    if e.status == 412:
                        # Etags mismatch: handle the exception.
                        pass

    @api.model
    def _do_request(self, uri, params=None, headers=None, type='POST', preuri="https://www.googleapis.com"):
        """
            Exécution d'une requête de type POST
        """
        params = params or {}
        headers = headers or {}
        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !", uri, type, headers, params)

        try:
            req = urllib2.Request(preuri + uri, params, headers)
            resp = urllib2.urlopen(req, timeout=TIMEOUT)
            resp.getcode()

        except urllib2.HTTPError, error:
            if error.code in (204, 404):
                raise error
            else:
                _logger.exception("Bad google request : %s !", error.read())
                if error.code in (400, 401, 410):
                    raise error
                raise self.env['res.config.settings'].get_config_warning(_("Something went wrong with your request "
                                                                           "to google"))

    def partner_infos(self, partner):
        """
            Récupération des données d'un res.partner
        """
        data = {
            'FullName': partner.name,
            'Email': partner.email or '',
            'Phone': partner.phone or '',
            'Phone2': partner.phone2 or '',
            'Mobile': partner.mobile or '',
            'Street': partner.street or '',
            'Street2': partner.street2 or '',
            'City': partner.city or '',
            'Region': partner.state_id.name or '',
            'Postcode': partner.zip or '',
            'Country': partner.country_id.name or ''
        }

        return data

    def get_google_scope(self):
        """
            Retourne le scope autorisant la lecture et écriture dans l'api Google Contacts
        """
        return 'https://www.googleapis.com/auth/contacts'

    @api.model
    def _get_google_token_uri(self, scope, redirect_uri):
        """
            Permet de calculer un code d'autorisation pour un scope donné à partir du client_id
        """
        parameters = self.env['ir.config_parameter'].sudo()
        client_id = parameters.get_param('google_contacts_client_id')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        menu_id = self.env.ref('contacts.menu_contacts').id
        action_id = self.env.ref('contacts.action_contacts').id
        debug = '?debug' if request.debug else ''
        adresse_de_redirection = base_url + '/web%s#menu_id=%d&action=%d' % (debug, menu_id, action_id)

        state = {
            'd': self.env.cr.dbname,
            's': 'contacts',
            'f': adresse_de_redirection
        }

        encoded_params = werkzeug.url_encode(dict(
            scope=scope,
            state=json.dumps(state),
            redirect_uri=redirect_uri,
            client_id=client_id,
            response_type='code',
            approval_prompt='force',
            access_type='offline'

        ))

        return '%s?%s' % ('https://accounts.google.com/o/oauth2/auth', encoded_params)

    @api.model
    def set_all_tokens(self, authorization_code):
        """
            Permet de calculer un access_token et un refresh_token à partir d'un code d'autorisation
        """
        all_token = self.env['google.service']._get_google_token_json(authorization_code, 'contacts')
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)

        vals = {}
        vals['google_contacts_rtoken'] = all_token.get('refresh_token')
        vals['google_contacts_token_validity'] = datetime.now() + timedelta(
            seconds=all_token.get('expires_in'))
        vals['google_contacts_token'] = all_token.get('access_token')
        current_user.sudo().write(vals)

    def do_refresh_token(self):
        """
            Permet de recalculer un nouvel access_token à l'aide du refresh_token quand l'access_token n'est plus
            valide (validité de 3600s)
        """
        user_to_sync = self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)
        all_token = self.env['google.service']._refresh_google_token_json(current_user.google_contacts_rtoken,
                                                                          'contacts')
        vals = {}
        vals['google_contacts_token_validity'] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_contacts_token'] = all_token.get('access_token')

        current_user.sudo().write(vals)
