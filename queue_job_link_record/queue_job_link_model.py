# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, api, _


class ProjectProject(models.Model):
    _inherit = 'queue.job'

    @api.multi
    def open_records(self):
        res = {}
        if len(self.record_ids) > 1:
            res = {
                'name': _(u"Linked Objects"),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': self.model_name,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.record_ids)]
            }
        elif len(self.record_ids) == 1:
            res = {
                'name': self.name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.model_name,
                'res_id': self.record_ids[0],
            }

        return res
