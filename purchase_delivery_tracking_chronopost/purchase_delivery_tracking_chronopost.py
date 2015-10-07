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
from lxml import etree

class ChronopostPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def update_delivery_status(self):
        super(ChronopostPurchaseOrder, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'Chronopost' and rec.state not in ['draft', 'cancel', 'done']:
                for track in rec.tracking_ids:
                    track.status_ids.unlink()
                    file = urlopen(_('https://www.chronopost.fr/tracking-cxf/TrackingServiceWS/trackSkybill?language=en_US&skybillNumber=') + track.name)
                    if file:
                        list_status = etree.fromstring(file.read()).findall(".//events")
                        for c in list_status:
                            date = c.find(".//eventDate").text
                            date = date[:10] + ' ' + date[11:19]
                            self.env['tracking.status'].create({'date': date,
                                                                'status': c.find(".//eventLabel").text,
                                                                'tracking_id': track.id})
