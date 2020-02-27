# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import urllib
import logging
from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class BetterZipWithUpdate(models.Model):
    _inherit = 'res.better.zip'

    country_id = fields.Many2one('res.country', 'Country', required=True)

    @api.multi
    def update_french_zipcodes(self):
        _logger.info(u"Started updating french zip codes database")
        france_id = self.env.ref('base.fr')

        already_known = set(self.env['res.better.zip'].search(
            [('country_id', '=', france_id.id)]).mapped(lambda x: (x.name, x.code)))

        ans = urllib.urlopen('https://datanova.legroupe.laposte.fr/explore/dataset/laposte_hexasmal/download/'
                             '?format=csv&timezone=Europe/Berlin&use_labels_for_header=true')
        ans.readline()

        for line in ans.readlines():
            line = line.strip()
            try:
                # TO CHECK: le format CSV a été modifié par La Poste, et ne correspond pas à sa propre doc.
                # À surveiller car doublon du libellé d'acheminement
                # Le format de la ligne suivante a été modifié le 25/02/2020
                code, city, name, city_complement, _, _, coordinates = line.split(';')
                latitude, longitude = (0, 0)
                coordinates = coordinates and unicode(coordinates).replace(u" ", u"")
                if coordinates:
                    splitted_coordinates = coordinates.split(u",")
                    if len(splitted_coordinates) == 2:
                        [latitude, longitude] = splitted_coordinates
                if city_complement:
                    city += " - %s" % city_complement
                _logger.info(u"Creating zip %s - %s from 'La Poste' API", name, city)
                if (name, code) not in already_known:
                    self.env['res.better.zip'].create({
                        'name': name,
                        'code': code,
                        'city': city,
                        'country_id': france_id.id,
                        'latitude': float(latitude),
                        'longitude': float(longitude),
                    })
            except ValueError:
                # If the current line's format is wrong
                pass

        _logger.info(u"Zip codes update succeed")
