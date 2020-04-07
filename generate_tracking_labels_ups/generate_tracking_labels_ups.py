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
import base64
import binascii
import logging
from io import BytesIO

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from PIL import Image
from PyPDF2 import PdfFileWriter, PdfFileReader
from openerp import models, api, fields, tools, modules
from openerp.exceptions import UserError
from ClassicUPS import UPSConnection

_logger = logging.getLogger(__name__)


class TrackingTransporter(models.Model):
    _inherit = 'tracking.transporter'

    api_login_ups = fields.Char(u"Login Api", required=True)
    api_password_ups = fields.Char(u"Mot de passe API", required=True)
    api_account_number_ups = fields.Char(u"Numéro de compte", required=True)
    api_token_ups = fields.Char(u"Token API", required=True)

    @api.multi
    def _check_valid_credencial(self):
        if self == self.env.ref('base_delivery_tracking_ups.transporter_ups'):
            mandatory_values = [
                self.api_login_ups,
                self.api_password_ups,
                self.api_account_number_ups,
                self.api_token_ups
            ]
            if any(not value for value in mandatory_values):
                raise UserError(u"Veuillez remplir la configuration UPS")


class GenerateTrackingLabelsWizardMR(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    @api.multi
    def generate_label(self):
        self.transport_id._check_valid_credencial()
        if self.transporter_id != self.env.ref('base_delivery_tracking_ups.transporter_ups'):
            return super(GenerateTrackingLabelsWizardMR, self).generate_label()

        ups = UPSConnection(
            license_number=self.transporter_id.api_token_ups,
            user_id=self.transporter_id.api_login_ups,
            password=self.transporter_id.api_password_ups,
            shipper_number=self.transporter_id.api_account_number_ups,
            debug=self.transporter_id.test_mode
        )
        from_addr = {
            'name': self.partner_orig_id.company_id.name,
            'address1': self.partner_orig_id.street,
            'city': self.partner_orig_id.city,
            'country': self.partner_orig_id.country_id.code,
            'state': self.partner_orig_id.state_id.name,
            'postal_code': self.partner_orig_id.zip,
            'phone': self.partner_orig_id.phone,
            'email': self.partner_orig_id.email
        }
        to_addr = {
            "attn": self.name,
            "name": self.company_name,
            "address1": self.line2,
            "address2": self.line0,
            "address3": self.line1,
            "city": self.city,
            "country": self.country_id.code,
            "postal_code": self.zip,
            "state": self.zip,
            "email": self.email,
            "phone": self.phone_number,
        }
        if self.id_relais:
            to_addr['location_id'] = self.id_relais
        shipping_service = {
            'code': self.produit_expedition_id.code,
            'desc': self.produit_expedition_id.display_name,
        }
        package_infos = [{
            'desc': package.name,
            'weight_unit': 'KGS',
            'fill_dimension': False,
            'weight': package.delivery_weight,
        } for package in self.package_ids]

        shipment = ups.create_shipment(
            from_addr=from_addr,
            to_addr=to_addr,
            package_infos=package_infos,
            file_format='GIF',
            shipping_service=shipping_service,
            description=self.picking_id.group_id.display_name,
            reference_numbers=self.package_ids.mapped('name')
        )
        trackings = []
        final_pdf = PdfFileWriter()
        myobj = StringIO()
        obj_close = [myobj]
        for pkg in shipment.package_results():
            trackings.append(pkg['tracking_number'])
            out_io = BytesIO()
            obj_close.append(out_io)
            Image.open(BytesIO(binascii.a2b_base64(pkg['label']))).transpose(Image.ROTATE_270).save(out_io, 'PDF')
            final_pdf.addPage(PdfFileReader(out_io).getPage(0))

        final_pdf.write(myobj)
        final_encoded_data = base64.encodestring(myobj.getvalue())

        if final_encoded_data:
            self.picking_id.write({
                'binary_label': final_encoded_data,
                'data_fname': self.get_output_file(),
            })

        for to_close in obj_close:
            to_close.close()
        return trackings
