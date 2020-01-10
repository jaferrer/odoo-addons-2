# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields


def binary_write(self, records, value):
    """ Monkeypatch of the odoo Binary field write method, in order to give a name to the created attachment """
    # retrieve the attachments that stores the value, and adapt them
    assert self.attachment
    domain = [
        ('res_model', '=', records._name),
        ('res_field', '=', self.name),
        ('res_id', 'in', records.ids),
    ]
    atts = records.env['ir.attachment'].sudo().search(domain)
    with records.env.norecompute():
        if value:
            # update the existing attachments
            atts.write({'datas': value})
            # create the missing attachments
            for record in records - records.browse(atts.mapped('res_id')):
                name = getattr(record, getattr(self, 'fname', self.name + '_fname'), self.name)
                atts.create({
                    'name': name,
                    'res_model': record._name,
                    'res_field': self.name,
                    'res_id': record.id,
                    'type': 'binary',
                    'datas': value,
                })
        else:
            atts.unlink()


fields.Binary.write = binary_write
