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
from urllib import urlencode


class ColissimoTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def _compute_logo(self):
        super(ColissimoTrackingNumber, self)._compute_logo()
        for rec in self:
            if rec.transporter_id.name == 'Colissimo':
                rec.logo = "/purchase_delivery_tracking_colissimo/static/img/colissimo.jpg"


class ColissimoPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def update_delivery_status(self):
        super(ColissimoPurchaseOrder, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'Colissimo' and rec.state not in ['draft', 'cancel', 'done']:
                for track in rec.tracking_ids:
                    track.status_ids.unlink()
                    post_response = urlopen('http://www.colissimo.fr/portail_colissimo/suivreResultatStubs.do',
                                            urlencode({"language": _("en_GB"), "parcelnumber": track.name}))
                    if post_response:
                        response_etree = etree.parse(post_response, etree.HTMLParser())
                        body = response_etree.xpath(".//tbody")
                        if body:
                            list_status = body[0].findall(".//tr")
                            if list_status:
                                for status in list_status:
                                    description_status = status.findall(".//td")
                                    description = ' '.join(description_status[1].text.split())
                                    if description_status[2].text and ' '.join(description_status[2].text.split()) != '':
                                        description = ' '.join(description_status[2].text.split()) + ' - ' + description
                                    date = description_status[0].text
                                    date = date[6:] + '-' + date[3:5] + '-' + date[:2] + ' 00:00:01'
                                    self.env['tracking.status'].create({'date': date,
                                                                        'status': description,
                                                                        'tracking_id': track.id})
