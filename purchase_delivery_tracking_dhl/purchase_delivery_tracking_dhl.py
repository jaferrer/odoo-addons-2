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

from openerp import models, fields, api, _
from urllib2 import urlopen
import json
from dateutil.parser import parse


class DhlTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def _compute_logo(self):
        super(DhlTrackingNumber, self)._compute_logo()
        for rec in self:
            if rec.transporter_id.name == 'DHL':
                rec.logo = "/purchase_delivery_tracking_dhl/static/img/dhl.jpg"


class DhlPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def update_delivery_status(self):
        super(DhlPurchaseOrder, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'DHL' and rec.state not in ['draft', 'cancel', 'done']:
                for track in rec.tracking_ids:
                    track.status_ids.unlink()
                    file_translated = urlopen('http://www.dhl.fr/shipmentTracking?AWB=' + track.name +
                                   _('&countryCode=fr&languageCode=en'))
                    file_english = urlopen('http://www.dhl.fr/shipmentTracking?AWB=' + track.name +
                                         '&countryCode=fr&languageCode=en')
                    if file_english and file_translated:
                        list_status_english = json.loads(file_english.read())
                        list_status_translated = json.loads(file_translated.read())
                        if list_status_english.get('results') and list_status_english['results'][0].get('checkpoints'):
                            for c in list_status_english['results'][0]['checkpoints']:
                                date = False
                                status = c.get('description') or ''
                                if c.get('date') and c.get('time'):
                                    date = fields.Date.to_string(parse(c['date'])) + ' ' + c['time'] + ':00'
                                for item in list_status_translated['results'][0]['checkpoints']:
                                    if item.get('counter') == c['counter']:
                                        status = item.get('description') or status
                                        break
                                self.env['tracking.status'].create({'date': date,
                                                                    'status': status,
                                                                    'tracking_id': track.id})
