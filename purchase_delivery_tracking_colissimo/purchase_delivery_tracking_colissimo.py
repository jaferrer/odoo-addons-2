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

import requests

from openerp import models, api


class ColissimoTrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    @api.multi
    def _compute_logo(self):
        super(ColissimoTrackingTransporter, self)._compute_logo()
        for rec in self:
            if rec.name == 'Colissimo':
                rec.logo = "/purchase_delivery_tracking_colissimo/static/img/colissimo.jpg"


class ColissimoTrackingNumber(models.Model):
    _inherit = 'tracking.number'

    @api.multi
    def update_delivery_status(self):
        super(ColissimoTrackingNumber, self).update_delivery_status()
        for rec in self:
            if rec.transporter_id.name == 'Colissimo':

                rec.status_ids.unlink()
                try:
                    headers = {
                        "Accept": "application/json",
                        "X-Okapi-Key": self.env['ir.config_parameter'].get_param("entrepot_project.token_chronopost")
                    }
                    response = requests.get(url="https://api.laposte.fr/suivi/v2/idships/%s?lang=fr_FR" % (rec.name),
                                            headers=headers)

                    if response.status_code != 200:
                        continue

                    events = response.json().get('shipment', {}).get('event', {})
                    for event in events:
                        self.env['tracking.status'].create({'date': event.get('date'),
                                                            'status': event.get('label', ''),
                                                            'tracking_id': rec.id})
                except:
                    pass
