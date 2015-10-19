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
from dateutil.parser import parse


class DpdTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def _compute_logo(self):
        super(DpdTrackingNumber, self)._compute_logo()
        for rec in self:
            if rec.transporter_id.name == 'DPD':
                rec.logo = "/purchase_delivery_tracking_dpd/static/img/dpd.png"


class DpdPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def update_delivery_status(self):
        super(DpdPurchaseOrder, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'DPD' and rec.state not in ['draft', 'cancel', 'done']:
                for track in rec.tracking_ids:
                    track.status_ids.unlink()
                    file = urlopen('https://tracking.dpd.de/cgi-bin/simpleTracking.cgi?parcelNr=' +
                                   track.name + '&locale=en_D2&type=1')
                    file_string = file.read()
                    data = json.loads(file_string[-len(file_string) + 1:-1])
                    if data.get('TrackingStatusJSON') and data['TrackingStatusJSON'].get('statusInfos'):

                        for item in data['TrackingStatusJSON']['statusInfos']:
                            if item.get('contents') and item['contents'][0].get('label'):
                                date = item['date']
                                date = parse(date[6:] + '-' + date[3:5] + '-' + date[:2] + ' ' + item['time'])
                                self.env['tracking.status'].create({'date': date,
                                                                    'status': item['city'] + ' - ' +
                                                                              item['contents'][0]['label'],
                                                                    'tracking_id': track.id})
