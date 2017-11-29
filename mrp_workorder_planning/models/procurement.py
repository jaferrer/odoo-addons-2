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

from odoo import fields, models


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    def _get_date_planned(self):
        """Returns the planned date for the production.order to be made from this procurement."""
        format_date_planned = fields.Datetime.from_string(self.date_planned)
        days = self.product_id.produce_delay + self.company_id.manufacturing_lead
        return self.company_id.schedule_working_days(-days, format_date_planned)
