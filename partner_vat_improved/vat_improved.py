# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.osv import osv


class res_partner_vat(models.Model):
    _inherit = "res.partner"

    @api.multi
    def check_vat(self):
        for rec in self:
            if len(rec.vat) < 2:
                raise osv.except_orm(_(u"Error !"), _(u"Your vat number length is less than 3"))
        super(res_partner_vat, self).check_vat()
