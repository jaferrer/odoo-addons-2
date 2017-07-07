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
from lxml import etree
from dateutil.parser import parse
import ssl


class TntTrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    @api.multi
    def _compute_logo(self):
        super(TntTrackingTransporter, self)._compute_logo()
        for rec in self:
            if rec.name == 'TNT':
                rec.logo = "/purchase_delivery_tracking_tnt/static/img/tnt.png"


class TntTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def update_delivery_status(self):
        super(TntTrackingNumber, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'TNT':
                rec.status_ids.unlink()
                unverified_context = ssl._create_unverified_context()
                file = urlopen('http://www.tnt.com/webtracker/tracking.do',
                                          urlencode({"cons": str(rec.name),
                                                     "genericSiteIdent": "",
                                                     "navigation": "0",
                                                     "page": "1",
                                                     "plazakey": "",
                                                     "refs": str(rec.name),
                                                     "requestType": "GEN",
                                                     "respCountry": "us",
                                                     "respLang": "en",
                                                     "searchType": "con",
                                                     "sourceCountry": "ww",
                                                     "sourceID": "1",
                                                     "trackType": "CON"}), context=unverified_context)
                html_file = etree.parse(file, etree.HTMLParser())
                list_status = html_file.xpath(".//table[@class='appTable']")
                if len(list_status) == 3:
                    list_status = list_status[1].findall("./tbody/tr")
                    for status in list_status:
                        status_items = status.findall(".//td")
                        if len(status_items) == 4 and status_items[0].text != 'Date':
                            date = parse('-'.join((status_items[0].text).split()) + ' ' +
                                         status_items[1].text.split()[0])
                            self.env['tracking.status'].create({'date': date,
                                                                'status': status_items[2].text + ' - ' +
                                                                          status_items[3].text,
                                                                'tracking_id': rec.id})
