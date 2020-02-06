# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    partner_non_eligible_factor = fields.Boolean(u"non eligible factor", readonly=True,
                                                 compute="_compute_partner_non_eligible_factor")

    allow_transmit_factor = fields.Boolean(u"Allow factor transmission")

    factor_needs_transmission = fields.Boolean(u"Needs factor transmission", readonly=True)
    factor_transmission_ids = fields.Many2many('factor.transmission', 'account_invoice_factor_transmission_rel',
                                               'account_invoice_id', 'factor_transmission_id',
                                               string=u"Factor transmission")

    @api.model
    def _is_factor_bank_correct(self, partner):
        factor_bank = partner and partner.commercial_partner_id and partner.commercial_partner_id.factor_bank_id
        return factor_bank and not factor_bank.get_factor_settings_errors() or False

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
                            payment_term=False, partner_bank_id=False, company_id=False, context=None):
        res = super(AccountInvoice, self).onchange_partner_id(type, partner_id, date_invoice,
                                                              payment_term, partner_bank_id, company_id)
        # set allow_transmit_factor default value
        factor_bank_ok = self._is_factor_bank_correct(self.env['res.partner'].browse(partner_id))
        res['value']['partner_non_eligible_factor'] = not factor_bank_ok
        res['value']['allow_transmit_factor'] = factor_bank_ok
        return res

    def on_new_payment(self):
        if self.state != 'paid' and self.allow_transmit_factor and not self.factor_needs_transmission:
            self.write({'factor_needs_transmission': True})

    @api.multi
    def resend_to_factor(self):
        self.ensure_one()
        self.factor_needs_transmission = True

    @api.multi
    @api.onchange('partner_id')
    def _compute_partner_non_eligible_factor(self):
        for rec in self:
            rec.partner_non_eligible_factor = not self._is_factor_bank_correct(rec.partner_id)

    @api.model
    def create(self, vals):
        if 'partner_id' in vals:
            partner = self.env['res.partner'].browse(vals['partner_id'])
            vals['allow_transmit_factor'] = self._is_factor_bank_correct(partner)
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice, self).write(vals)
        for rec in self:
            if rec.allow_transmit_factor and rec.partner_non_eligible_factor:
                rec.allow_transmit_factor = False
        return res
