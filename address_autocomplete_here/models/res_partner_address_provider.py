# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartnerHereAddress(models.Model):
    _name = 'res.partner.address.provider'

    name = fields.Char(u"Adresse")
    language = fields.Char(u"language")
    countryCode = fields.Char(u"country code")
    matchLevel = fields.Char(u"match level")
    label = fields.Char(u"label")
    locationId = fields.Char(u"location id")
    city = fields.Char(u"ville")
    country = fields.Char(u"Pays")
    county = fields.Char(u"Département")
    state = fields.Char(u"Région")
    street = fields.Char(u"Rue")
    postalCode = fields.Char(u"Code Postal")
    houseNumber = fields.Char(u"Numéro")

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super(ResPartnerHereAddress, self).name_search(name, args, operator, limit)

        if len(res) < limit:
            addresses = self.request_address(name)
            for address in addresses:
                result = self.search([('locationId', '=', address['locationId'])])
                if not result:
                    result = self.create(address)
                res.append((result.id, result.label))
        return res

    @api.multi
    def request_address(self, request):
        url = self.env['ir.config_parameter'].get_param('address_autocomplete.url_address_provider')
        if not url:
            raise UserError(u"L'adresse du site de Géocoding Here n'est pas renseigné")
        login = self.env['ir.config_parameter'].get_param('address_autocomplete.login_address_provider')
        if not login:
            raise UserError(u"L'identifiant du site de Géocoding Here n'est pas renseigné")
        password = self.env['ir.config_parameter'].get_param('address_autocomplete.password_address_provider')
        if not password:
            raise UserError(u"Le mot de passe du site de Géocoding Here n'est pas renseigné")
        pays = self.env['ir.config_parameter'].get_param('address_autocomplete.country_address_provider')
        if not pays:
            raise UserError(u"Il n'y a pas de pays renseigné pour lequel appliquer la recherche")

        demande = {'app_id': login,
                   'app_code': password,
                   'query': request,
                   'country': pays,
                   'beginHighlight': '',
                   'endHighlight': ''}
        requete = requests.get(url, params=demande)
        suggestions = requete.json().get('suggestions', [])

        return [{
            'name': suggestion.get('label'),
            'language': suggestion.get('language'),
            'countryCode': suggestion.get('countryCode'),
            'matchLevel': suggestion.get('matchLevel'),
            'label': suggestion.get('label'),
            'locationId': suggestion.get('locationId'),
            'city': suggestion.get('address', {}).get('city'),
            'country': suggestion.get('address', {}).get('country'),
            'county': suggestion.get('address', {}).get('county'),
            'state': suggestion.get('address', {}).get('state'),
            'street': suggestion.get('address', {}).get('street'),
            'postalCode': suggestion.get('address', {}).get('postalCode'),
            'houseNumber': suggestion.get('address', {}).get('houseNumber')
        } for suggestion in suggestions]
