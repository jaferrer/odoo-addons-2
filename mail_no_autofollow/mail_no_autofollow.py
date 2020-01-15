# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo.tools import config
from odoo import models, api


class MailThreadExtended(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, force=True):
        if partner_ids and not config["test_enable"]:
            users = self.env['res.users'].search([('partner_id', 'in', partner_ids)])
            partner_ids = [user.partner_id.id for user in users]
        return super(MailThreadExtended, self).message_subscribe(partner_ids=partner_ids,
                                                                 channel_ids=channel_ids,
                                                                 subtype_ids=subtype_ids,
                                                                 force=force)
