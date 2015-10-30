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


class FedexTrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    @api.multi
    def _compute_logo(self):
        super(FedexTrackingTransporter, self)._compute_logo()
        for rec in self:
            if rec.name == 'FedEx':
                rec.logo = "/purchase_delivery_tracking_fedex/static/img/fedex.png"


class FedexTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def update_delivery_status(self):
        super(FedexTrackingNumber, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'FedEx':
                print 'track unlink', rec, rec.name
                rec.status_ids.unlink()
                print rec.status_ids
                file_translated = urlopen('https://www.fedex.com/trackingCal/track',
                                          urlencode({"data": '{"TrackPackagesRequest":{"appType":"WTRK",'
                                                             '"uniqueKey":"","processingParameters":{},'
                                                             '"trackingInfoList":[{"trackNumberInfo":'
                                                             '{"trackingNumber":"%s","trackingQualifier":'
                                                             '"","trackingCarrier":""}}]}}' % (rec.name,),
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
                                                                'tracking_id': rec.id})
