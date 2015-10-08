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
from urllib import urlencode
import json

class FedexPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def update_delivery_status(self):
        super(FedexPurchaseOrder, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'FedEx' and rec.state not in ['draft', 'cancel', 'done']:
                for track in rec.tracking_ids:
                    track.status_ids.unlink()
                    file_translated = urlopen('https://www.fedex.com/trackingCal/track',
                                              urlencode({"data": '{"TrackPackagesRequest":{"appType":"WTRK",'
                                                                 '"uniqueKey":"","processingParameters":{},'
                                                                 '"trackingInfoList":[{"trackNumberInfo":'
                                                                 '{"trackingNumber":"652920832306","trackingQualifier":'
                                                                 '"","trackingCarrier":""}}]}}',
                                                         "action": "trackpackages",
                                                         "locale": _("en_EN"),
                                                         "version": "1",
                                                         "format": "json"}))

                    list_status_english = json.loads(file_translated.read())
                    if list_status_english.get('TrackPackagesResponse').get('packageList') and \
                            list_status_english['TrackPackagesResponse']['packageList'][0].get('scanEventList'):
                        for item in list_status_english['TrackPackagesResponse']['packageList'][0]['scanEventList']:
                            if item.get('status') and item.get('date') and item.get('time'):
                                self.env['tracking.status'].create({'date': item['date'] + ' ' + item['time'],
                                                                    'status': item['status'],
                                                                    'tracking_id': track.id})
