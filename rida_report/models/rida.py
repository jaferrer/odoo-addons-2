# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api


class RidaReport(models.Model):
    _name = 'rida.report'

    name = fields.Char(u"Name", required=True)
    theme_id = fields.Many2one('res.partner', u"Theme", required=True)
    project_id = fields.Many2one('project.project', u"Related project", required=True)
    creation_date = fields.Date(u"Creation date", required=True, default=fields.Date.today)
    line_ids = fields.One2many('rida.line', 'report_id', u"Lines")


class RidaLine(models.Model):
    _name = 'rida.line'

    type = fields.Selection([
        ('information', u"Information"),
        ('decision', u"Decision"),
        ('action', u"Action")
    ], u"Type", required=True)
    name = fields.Char(u"Description", required=True)
    user_id = fields.Many2one('res.users', u"Related user")
    date = fields.Date(u"Expected date")
    report_id = fields.Many2one('rida.report', u"Related RIDA", required=True)

    # The following field only exists if type is 'action'
    state = fields.Selection([
        ('normal', u"To do"),
        ('done', u"Done"),
    ], u"Line state", default='normal')

    @api.multi
    @api.onchange('type')
    def _onchange_type(self):
        self.ensure_one()
        if self.type == 'action':
            self.date = fields.Date.today()
            self.user_id = self.env.user
        else:
            self.date = False
            self.user_id = False
