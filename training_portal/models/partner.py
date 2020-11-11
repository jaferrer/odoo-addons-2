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


class TrainingPortalResPartner(models.Model):
    _inherit = 'res.partner'

    def give_access_to_trainer(self):
        group_portal = self.env.ref('base.group_portal')
        group_trainer = self.env.ref('training_base.group_training_trainer')
        for rec in self:
            wizard = self.env['portal.wizard'].create({'user_ids': [(0, 0, {'partner_id': rec.id,
                                                                            'email': rec.email,
                                                                            'in_portal': True})]})
            wizard.action_apply()
            for user in rec.user_ids:
                group_ids = user.groups_id.ids
                if group_trainer.id not in group_ids:
                    group_ids += [group_trainer.id]
                    if group_portal.id in group_ids:
                        group_ids = [group_id for group_id in group_ids if group_id != group_portal.id]
                    user.write({'groups_id': [(6, 0, group_ids)]})
