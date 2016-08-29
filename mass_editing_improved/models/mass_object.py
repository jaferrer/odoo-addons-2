# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C):
#        2012-Today Serpent Consulting Services (<http://www.serpentcs.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import fields, models, api, _


class MassObject(models.Model):
    _inherit = 'mass.object'

    sub_model_id = fields.Many2one('ir.model.fields', u"Sub Model")

    @api.multi
    def onchange_model_id(self, model_id):
        result = super(MassObject, self).onchange_model_id(model_id)
        result['value']['sub_model_id'] = False
        return result

    @api.onchange('sub_model_id')
    def onchange_sub_model_id(self):
        self.ensure_one()
        if self.sub_model_id:
            id_sub = self.env['ir.model'].search([('model', '=', self.sub_model_id.relation)]).id
            self.model_ids = self.onchange_model_id(id_sub)['value']['model_ids']
        else:
            self.model_ids = [(5, 0, 0)]

        self.fields_id = [(5, 0, 0)]
