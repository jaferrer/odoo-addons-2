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

from odoo import models


class Ean13Checksum(models.AbstractModel):
    _name = 'abstract.ean13.checksum'
    _description = 'abstract.ean13.checksum'

    def calculate_checksum(self, barcode):
        evensum = 0
        oddsum = 0
        if len(barcode) != 12:
            return False
        for i, v in enumerate(barcode):
            if (i % 2) == 0:
                evensum += int(v)
            else:
                oddsum += int(v)
        return str((10 - ((evensum + oddsum * 3) % 10)) % 10)

    def check_checksum(self, barcode):
        if len(barcode) != 13:
            return False
        return self.calculate_checksum(barcode[:12]) == barcode[12:]
