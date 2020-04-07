# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import logging

from odoo import models, api, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def chronopost_rate_shipment(self, order):
        return self.fixed_rate_shipment(order)

    def chronopost_send_shipping(self):
        pass
        # C'est dans cette methode que les etiquettes sont générées. Pour ce faire il faut appeler la methode shippingMultiParcelWithReservation de la wsdl de chronopost.
        # Tous le code ce trouve dans generate_tracking_labels_chronopost/generate_tracking_labels_chronopost.py
        # Le but est que le code soit plus clair et d'eviter d'appeler la wsdl directement en string et utiliser un lib python: zeep ou suds

    def chronopost_get_tracking_link(self):
        pass
        # retourner https://www.chronopost.fr/tracking-no-cms/suivi-page?listeNumerosLT=

    def chronopost_cancel_shipment(self):
        pass

    def chronopost_get_default_custom_package_code(self):
        pass
