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

from odoo import http
from odoo.http import Response, request


class GetPartnerNode(http.Controller):

    @http.route('/get_parent_node', type='http', auth='user', website=True)
    def get_parent_node(self, node_id):
        parent_partner = request.env['res.partner'].browse(int(node_id)).parent_id
        result = {
            'id': parent_partner.id,
            'display_name': parent_partner.display_name,
            'function': parent_partner.function,
            'email': parent_partner.email,
            'company_type': parent_partner.company_type,
            'relationship': parent_partner.relationship,
        }
        return Response(json.dumps(result), content_type='application/json;charset=utf-8', status=200)

    @http.route('/get_children_nodes', type='http', auth='user', website=True)
    def get_children_nodes(self, node_id):
        partner = request.env['res.partner'].browse(int(node_id))
        result = {'children': []}
        for child in partner.child_ids:
            result['children'].append({
                'id': child.id,
                'display_name': child.display_name,
                'function': child.function,
                'email': child.email,
                'company_type': child.company_type,
                'relationship': child.relationship,
            })
        return Response(json.dumps(result), content_type='application/json;charset=utf-8', status=200)
