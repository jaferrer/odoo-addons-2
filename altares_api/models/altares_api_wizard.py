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
import ast

from urllib import parse
import requests

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AltaresApiWizard(models.TransientModel):
    _name = 'altares.api.wizard'

    partner_ids = fields.Many2many('res.partner', string="Societies", domain=[('is_company', '=', True)])

    @api.model
    def connection_error_msg(self, response):
        error_msg = ast.literal_eval(response.text)['TransactionResult'].get('ResultText')
        raise UserError(_("HTTP Request returned a %d error :\n %s" % (response.status_code, error_msg)))

    @api.multi
    def get_token(self):
        """
        Altares token are valid for 24h.
        """
        self.ensure_one()
        user_id_altares = self.env['ir.config_parameter'].get_param('altares_api.user_id_altares')
        user_password_altares = self.env['ir.config_parameter'].get_param('altares_api.user_password_altares')
        headers = {
            'x-dnb-user': user_id_altares,
            'x-dnb-pwd': user_password_altares
        }
        # Session de test
        # headers = {
        #     'x-dnb-user': "P200000D2D9AB33F1ED47A1B7E752D7B",
        #     'x-dnb-pwd': "totototo"
        # }
        url = "https://direct.dnb.com/Authentication/V2.0/"
        response = requests.post(url, headers=headers)
        if response.status_code != 200:
            self.connection_error_msg(response)
        token_dico = response.json()

        return token_dico['AuthenticationDetail'].get('Token')

    @api.multi
    def get_duns_number(self, token, partner):
        """
        DUNS number or 'Match' is equivalent to a unique id for Altares.
        """
        if not partner.altares_duns_number:
            headers = {
                'Authorization': token
            }
            params = {
                'CountryISOAlpha2Code': "FR",
                'SubjectName': partner.name.upper(),
                'match': True,
                'MatchTypeText': "Advanced",
            }
            encoded_params = parse.urlencode(params)
            url = "https://direct.dnb.com/V5.0/organizations?" + encoded_params

            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                self.connection_error_msg(response)
            response_dico = response.json()
            partner.altares_duns_number = \
                response_dico['MatchResponse']['MatchResponseDetail']['MatchCandidate'][0].get('DUNSNumber')
            # Session de test
            # partner.altares_duns_number = '804735132'

        return partner.altares_duns_number

    @api.multi
    def get_altares_grade(self, partner):
        token = self.get_token()
        duns_number = self.get_duns_number(token, partner)
        headers = {
            'Authorization': token
        }
        url = "https://direct.dnb.com/V5.0/organizations/%s/products/VIAB_RAT" % duns_number

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.connection_error_msg(response)
        response_dico = response.json()

        orga_infos = response_dico['OrderProductResponse']['OrderProductResponseDetail']['Product']['Organization']
        grades_infos = orga_infos['Assessment']['DNBViabilityRating']
        viability_rating = grades_infos.get('DNBViabilityRating')
        viability_score = grades_infos['ViabilityScore']['RiskLevelDescription'].get('$')
        portfolio_comparison = grades_infos['PortfolioComparisonScore']['RiskLevelDescription'].get('$')
        data_depth_indicator = "\n".join(grades_infos['DataDepthDetail'].get('AssessmentText'))
        company_profile = \
            "\n".join(grades_infos['OrganizationProfileDetail']['TradeDataAvailabilityDetail'].get('AssessmentText'))

        return viability_rating, viability_score, portfolio_comparison, data_depth_indicator, company_profile

    @api.multi
    def do_update_altares_grades(self):
        """
        Update Altares DUNS number and viability grades for selected or all company partners.
        """
        self.ensure_one()
        all_partners = self.partner_ids or self.env['res.partner'].search([('is_company', '=', True)])
        for partner in all_partners:
            viability_rating, viability_score, portfolio_comparison, data_depth_indicator, company_profile = \
                self.get_altares_grade(partner)
            partner.write({
                'viability_rating': viability_rating,
                'viability_score': viability_score,
                'portfolio_comparison': portfolio_comparison,
                'data_depth_indicator': data_depth_indicator,
                'company_profile': company_profile,
            })
