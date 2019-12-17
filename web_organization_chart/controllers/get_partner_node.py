# -*- coding: utf-8 -*-
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

from odoo import http, api
from odoo.http import Response, request


class GetPartnerNode(http.Controller):

    @http.route('/get_init_data', type='http', auth='user', website=True)
    def get_init_data(self, node_id):
        partner = request.env['res.partner'].browse(int(node_id))
        while partner.parent_id:
            partner = partner.parent_id
        result = self.get_all_hierachy(partner)
        return Response(json.dumps(result), content_type='application/json;charset=utf-8', status=200)

    @api.model
    def get_all_hierachy(self, node):
        result = {
            'id': node.id,
            'display_name': node.display_name,
            'function': node.function,
            'email': node.email,
            'company_type': node.company_type,
            'children': []
        }
        for child in node.child_ids:
            result['children'].append(self.get_all_hierachy(child))
        return result
