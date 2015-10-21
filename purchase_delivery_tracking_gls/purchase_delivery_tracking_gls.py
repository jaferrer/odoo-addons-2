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


class GlsTrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    @api.multi
    def _compute_logo(self):
        super(GlsTrackingTransporter, self)._compute_logo()
        for rec in self:
            if rec.name == 'GLS':
                rec.logo = "/purchase_delivery_tracking_gls/static/img/gls.gif"


class GlsPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def update_delivery_status(self):
        super(GlsPurchaseOrder, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'GLS' and rec.state not in ['draft', 'cancel', 'done']:
                for track in rec.tracking_ids:
                    file = False
                    track.status_ids.unlink()
                    try:
                        file = urlopen(_('https://gls-group.eu/app/service/open/rest/EN/en/rstt001?match=') +
                                       track.name + '&caller=witt002&milis=1444824770093')
                    except:
                        pass
                    if file:
                        list_status = json.loads(file.read())
                        if list_status.get('tuStatus'):
                            for status in list_status['tuStatus'][0].get('history'):
                                if status.get('address') and status['address'].get('countryName') and \
                                        status['address'].get('city'):
                                    description = status['address']['city'] + ' (' + status['address']['countryName'] \
                                                  + ') - ' + status['evtDscr']
                                self.env['tracking.status'].create({'date': status['date'] + ' ' + status['time'],
                                                                    'status': description,
                                                                    'tracking_id': track.id})
