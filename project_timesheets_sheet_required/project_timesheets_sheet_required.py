# -*- coding: utf8 -*-
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

from odoo import models, api, _
from odoo.exceptions import ValidationError


class TimesheetSheetRequired(models.Model):
    _inherit = 'account.analytic.line'

    @api.constrains('project_id', 'sheet_id')
    def check_timesheet_sheet(self):
        if any([rec.project_id and not rec.sheet_id for rec in self]):
            raise ValidationError(_(u"It is forbidden to create a timesheet with no sheet."))
