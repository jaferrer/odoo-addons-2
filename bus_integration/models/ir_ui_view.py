# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api
from openerp.osv import orm


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def postprocess(self, model, node, view_id, in_tree_view, model_fields):
        res = super(IrUIView, self).postprocess(model, node, view_id, in_tree_view, model_fields)
        if node.tag == 'label' and node.get('for') and node.get('string'):
            mapping_field = self.env['bus.object.mapping.field'].search([('model_id.model', '=', model),
                                                                         ('field_id.name', '=', node.get('for'))])
            if mapping_field.mapping_id.is_exportable:
                node.set('string', u"⇐ %s" % node.get('string'))
            elif mapping_field.mapping_id.is_importable:
                node.set('string', u"⇒ %s" % node.get('string'))
            if mapping_field.mapping_id.is_importable and mapping_field.mapping_id.update_prohibited:
                orm.transfer_modifiers_to_node({'readonly': True}, node)
        if node.tag == 'field':
            mapping_field = self.env['bus.object.mapping.field'].search([('model_id.model', '=', model),
                                                                         ('field_id.name', '=', node.get('name'))])
            if mapping_field.mapping_id.is_importable and mapping_field.mapping_id.update_prohibited:
                orm.transfer_modifiers_to_node({'readonly': True}, node)
        return res
