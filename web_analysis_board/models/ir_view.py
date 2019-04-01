# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api, exceptions

ANALYSIS_VIEW = ('analysis', 'Analysis')


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[ANALYSIS_VIEW])

    @api.model
    def postprocess(self, model, node, view_id, in_tree_view, model_fields):
        res = super(IrUiView, self).postprocess(model, node, view_id, in_tree_view, model_fields)
        if node.tag in ('aggregate', 'formula'):
            field_name = node.get('field')
            if field_name:
                field = model_fields.get(field_name)
                if not field:
                    raise exceptions.UserError(u"Unknown field %s in model %s" % (field_name, model))
                res[node.get('field')] = {}
        return res
