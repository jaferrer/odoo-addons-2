# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import fields, models, api


class procurement_working_days(models.Model):
    _inherit = "procurement.order"

    @api.model
    def _get_date_planned(self, procurement):
        """Returns the planned date for the production.order to be made from this procurement."""
        calendar_id, resource_id = procurement._get_move_calendar()
        format_date_planned = datetime.strptime(procurement.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        date_planned = procurement._schedule_working_days(-procurement.product_id.produce_delay or 0.0,
                                                          format_date_planned,
                                                          resource_id,
                                                          calendar_id)
        date_planned = procurement._schedule_working_days(-procurement.company_id.manufacturing_lead,
                                                          date_planned,
                                                          resource_id,
                                                          calendar_id)
        return date_planned
