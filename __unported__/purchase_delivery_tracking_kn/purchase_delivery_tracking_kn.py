# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, _
from urllib2 import urlopen
import json


class KnTrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    @api.multi
    def _compute_logo(self):
        super(KnTrackingTransporter, self)._compute_logo()
        for rec in self:
            if rec.name == 'Kuehne Nagel':
                rec.logo = "/purchase_delivery_tracking_kn/static/img/kn.jpg"
