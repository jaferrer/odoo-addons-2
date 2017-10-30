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

from openerp import models, api
from urllib2 import urlopen
from lxml import etree
from urllib import urlencode
from dateutil.parser import parse
import requests


class UpsTrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    @api.multi
    def _compute_logo(self):
        super(UpsTrackingTransporter, self)._compute_logo()
        for rec in self:
            if rec.name == 'UPS':
                rec.logo = "/purchase_delivery_tracking_ups/static/img/ups.jpg"


class UpsTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def update_delivery_status(self):

        lang = self.env.user.lang

        def format(day_string):
            day_split = day_string.split('/')
            if len(day_split) == 3:
                if 'en' in lang:
                    return day_split[2] + '-' + day_split[0] + '-' + day_split[1]
                elif 'fr' in lang:
                    return day_split[2] + '-' + day_split[1] + '-' + day_split[0]
            return False

        super(UpsTrackingNumber, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'UPS':
                rec.status_ids.unlink()

                # First get
                params = {'HTMLVersion': '5.0', 'loc': lang, 'track.x': 'Suivi', 'trackNums': rec.name}
                r = requests.get('http://wwwapps.ups.com/WebTracking/track', params=params)
                file_etree = etree.fromstring(r.content, etree.HTMLParser())
                input_loc = file_etree.xpath(".//form[@id='detailFormid']/input[@name='loc']")
                input_USER_HISTORY_LIST = file_etree.xpath(".//form[@id='detailFormid']/input[@name='USER_HISTORY_LIST']")
                input_progressIsLoaded = file_etree.xpath(".//form[@id='detailFormid']/input[@name='progressIsLoaded']")
                input_refresh_sii_id = file_etree.xpath(".//form[@id='detailFormid']/input[@name='refresh_sii_id']")
                input_datakey = file_etree.xpath(".//form[@id='detailFormid']/input[@name='datakey']")
                input_HIDDEN_FIELD_SESSION = file_etree.xpath(".//form[@id='detailFormid']/input[@name='HIDDEN_FIELD_SESSION']")
                input_multiship = file_etree.xpath(".//form[@id='detailFormid']/input[@name='multiship']")

                new_key = 'descValue' + rec.name

                values = {"loc": input_loc and input_loc[0].get('value') or '',
                          "USER_HISTORY_LIST": input_USER_HISTORY_LIST and input_USER_HISTORY_LIST[0].get('value') or '',
                          "progressIsLoaded": input_progressIsLoaded and input_progressIsLoaded[0].get('value') or '',

                          "refresh_sii": input_refresh_sii_id and input_refresh_sii_id[0].get('value') or '',
                          "showSpPkgProg1": 'true',
                          "datakey": input_datakey and input_datakey[0].get('value') or '',
                          "HIDDEN_FIELD_SESSION": input_HIDDEN_FIELD_SESSION and input_HIDDEN_FIELD_SESSION[0].get('value') or '',
                          "multiship": input_multiship and input_multiship[0].get('value') or '',
                          'trackNums': '1ZA15Y100491770839',
                          new_key: ''}

                r = requests.post('https://wwwapps.ups.com/WebTracking/detail', data=values)
                response_etree = etree.fromstring(r.content, etree.HTMLParser())

                dataTable = response_etree.xpath(".//table[@class='dataTable']")
                if dataTable:
                    list_status = dataTable[0].findall(".//tr")
                    list_status = list_status and list_status[1:] or list_status
                    list_status_strings = []
                    current_location = ''

                    # Formating the result and creating status lines
                    for status in list_status:
                        properties = status.findall(".//td")
                        if properties:
                            property_strings = []
                            for property in properties:
                                new_prop = ' '.join(property.text.split())
                                if new_prop:
                                    property_strings += [new_prop]
                            if len(property_strings) == 4:
                                current_location = property_strings[0]
                            if len(property_strings) == 3:
                                property_strings = [current_location] + property_strings
                            list_status_strings += [property_strings]
                    for status in list_status_strings:
                        string_time = status[2]
                        string_date = format(status[1])
                        self.env['tracking.status'].create({'date': parse(string_date + ' ' + string_time),
                                                            'status': status[0] + ' - '+ status[3],
                                                            'tracking_id': rec.id})
