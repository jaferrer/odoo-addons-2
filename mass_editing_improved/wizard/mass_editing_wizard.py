# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
##############################################################################

from openerp import models, api, exceptions, _


class MassEditingWizardImproved(models.TransientModel):
    _inherit = 'mass.editing.wizard'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = False
        if self.env.context.get('mass_editing_object'):
            mass_object = self.env['mass.object'].browse(self.env.context.get('mass_editing_object'))

            # check if wizard fields are available for the current user. fields might be unreachable if 'groups=' is
            # specified on the field declaration
            if mass_object.field_ids:
                model_name = mass_object.field_ids[0].model
                model = self.env[model_name]
                for field in mass_object.field_ids:
                    if not model.fields_get().get(field.name):
                        raise exceptions.ValidationError(_("Mass editing can't be opened, you don't have access "
                                                           "to %s.%s field") % (model_name, field.name))

            if mass_object.sub_model_id:
                result = super(MassEditingWizardImproved,
                               self.with_context(active_model=mass_object.sub_model_id.relation)). \
                    fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if not result:
            result = super(MassEditingWizardImproved, self). \
                fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return result

    @api.model
    def create(self, vals):
        result = False
        if self.env.context.get('active_model') and self.env.context.get('mass_editing_object'):
            mass_object = self.env['mass.object'].browse(self.env.context.get('mass_editing_object'))
            # id_sub = self.env['ir.model'].search([('model', '=', self.env.context.get('active_model'))]).id
            # mass_object = self.env['ir.model'].browse(id_sub)
            if mass_object.sub_model_id:
                list_sub_model = self.env[self.env.context.get('active_model')]. \
                    browse(self.env.context.get('active_ids')).read([mass_object.sub_model_id.name])
                list_id = [ids[mass_object.sub_model_id.name][0] for ids in list_sub_model]

                result = super(MassEditingWizardImproved,
                               self.with_context(active_model=mass_object.sub_model_id.relation, active_ids=list_id)). \
                    create(vals)

        if not result:
            result = super(MassEditingWizardImproved, self).create(vals)

        return result
