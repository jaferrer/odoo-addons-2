# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields, api
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    purchase_line_subcontract_id = fields.Many2one('purchase.order.line', u"Ligne d'achat", copy=False, readonly=True)
    order_line_subcontract_id = fields.Many2one('purchase.order', u"Commande d'achat", readonly=True, copy=False,
                                                related='purchase_line_subcontract_id.order_id')
    subcontractor_id = fields.Many2one('res.partner', u"Sous-traitant", readonly=True, copy=False,
                                       related='purchase_line_subcontract_id.partner_id')
    warning_subcontractor = fields.Char(u"Message warning", compute='_compute_warning_subcontractor')

    state = fields.Selection(track_visibility='onchange')

    def _compute_warning_subcontractor(self):
        self.warning_subcontractor = "Ordre de fabrication sous-traité par %s" % self.subcontractor_id.display_name

    @api.multi
    def write(self, vals):
        self._assert_no_subcontracted()
        super(MrpProduction, self).write(vals)

    @api.multi
    def unlink(self):
        self._assert_no_subcontracted()
        super(MrpProduction, self).unlink()

    @api.multi
    def action_subcontracting_sended(self):
        self.with_context(force_edit=True, tracking_disable=True).action_cancel()
        self.with_context(force_edit=True).write({'state': 'progress'})

    @api.multi
    def action_subcontracting_cancel(self):
        self.with_context(force_edit=True).action_cancel()

    @api.multi
    def action_subcontracting_done(self):
        self.with_context(force_edit=True).write({'state': 'done'})

    @api.multi
    def _assert_no_subcontracted(self):
        if not self.env.context.get('force_edit'):
            for rec in self:
                if rec.purchase_line_subcontract_id:
                    raise UserError(
                        u"Vous ne pouvez modifier l'ordre de fabrication car il est lié à un sous-traitant.")
