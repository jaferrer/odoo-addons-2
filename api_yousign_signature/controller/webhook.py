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

from odoo import http
from odoo.http import request


class ApiYousignWebhook(http.Controller):

    # @http.route('/api/orders', type='json', methods=['POST'], auth='public', website=True, csrf=False)
    # def search_users(self, **kwargs):
    #     # Vérification du token
    #     token_header = request.httprequest.headers.get('X-API-Key') or request.httprequest.headers.get('Token')
    #     if token_header:
    #         token_value = request.env['ir.config_parameter'].sudo().get_param('ws_order_token')
    #         if token_header != token_value:
    #             raise exceptions.UserError("Erreur : Valeur du token erronée")
    #     else:
    #         raise exceptions.UserError("Erreur : Paramètre 'Token' inexistant")
    #     _logger.info(kwargs)
    #     request.env['sale.order'].process_create_web_commande(kwargs, jobify=True)

    @http.route("/yousign/webhook/procedure_started", type='json', methods=['POST'], auth='public', website=True, csrf=False)
    def catch_webhook(self, **kwargs):
        print('hello')
