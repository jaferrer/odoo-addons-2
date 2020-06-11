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
from odoo import http, exceptions
from odoo.http import request


class ApiYousignWebhook(http.Controller):

    @http.route("/yousign/webhook/procedure_started",
                type='json',
                methods=['POST'],
                auth='public',
                website=True,
                csrf=False)
    def catch_webhook_procedure(self, **kwargs):
        """
        Called when a new Yousign signature procedure is created.
        """
        x_api_key = request.jsonrequest.get(
            'procedure').get('config').get('webhook').get('procedure.started')[0].get('headers').get('X-API-Key')
        if x_api_key:
            webhook_key = request.env['ir.config_parameter'].sudo().get_param('reanova.yousign_webhook_key')
            if x_api_key != webhook_key:
                raise exceptions.UserError("Error : Invalid API-Key value.")
        else:
            raise exceptions.UserError("Error : API-Key not found.")

        return True

    @http.route("/yousign/webhook/member_finished",
                type='json',
                methods=['POST'],
                auth='public',
                website=True,
                csrf=False)
    def catch_webhook_signature(self, **kwargs):
        """
        Called when a Yousign document is signed by the client.
        """
        # Vérification de la clef
        x_api_key = request.jsonrequest.get(
            'procedure').get('config').get('webhook').get('procedure.started')[0].get('headers').get('X-API-Key')
        if x_api_key:
            webhook_key = request.env['ir.config_parameter'].sudo().get_param('reanova.yousign_webhook_key')
            if x_api_key != webhook_key:
                raise exceptions.UserError("Error : Invalid API-Key value.")
        else:
            raise exceptions.UserError("Error : API-Key not found.")

        return True
