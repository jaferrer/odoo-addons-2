# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api
from odoo.addons.base.ir import ir_actions

TIMELINE2 = ('timeline2', 'Timeline 2')
ir_actions.VIEW_TYPES.append(TIMELINE2)


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[TIMELINE2])


class DelegateTimeline(models.AbstractModel):
    _name = 'timeline2.delegate'
    _description = u"An abstract model to auto manage delegate feature in timeline2 view"

    @api.multi
    def delegate_write(self, write_info):
        vals = write_info.get('delegate_data', {})
        impacted = self.search([(write_info['delegate_field'], '=', write_info['delegate_id'])])
        impacted.mapped(write_info['delegate_field']).write(vals)
        return impacted.ids

    @api.model
    def delegate_create(self, create_info):
        vals = create_info.get('delegate_data', {})
        res = self.env[create_info['delegate_relation']].create(vals)
        return self.search([(create_info['delegate_field'], '=', res.id)]).ids

    @api.multi
    def delegate_unlink(self, unlink_info):
        impacted = self.search([(unlink_info['delegate_field'], '=', unlink_info['delegate_id'])])
        impacted_ids = impacted.ids
        impacted.mapped(unlink_info['delegate_field']).unlink()
        return impacted_ids
