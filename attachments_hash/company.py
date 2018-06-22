# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_attachments_cert_sequence_id = fields.Many2one('ir.sequence')

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if company._is_accounting_unalterable():
            sequence_fields = ['l10n_fr_attachments_cert_sequence_id']
            company._create_secure_sequence(sequence_fields)
        return company

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_attachments_cert_sequence_id']
                company._create_secure_sequence(sequence_fields)
        return res
