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

from openerp import models, fields, api


class NdpSaleConsuLine(models.Model):
    _name = 'ndp.sale.consu.line'

    name = fields.Char(u"Name")
    ndp_analytic_contract_id = fields.Many2one('ndp.analytic.contract',
                                               string=u"Contract",
                                               related='consu_group_id.ndp_analytic_contract_id')
    product_id = fields.Many2one('product.product', string=u"Service", required=True)
    date = fields.Date(u"Date", required=True)
    auto_invoice = fields.Boolean(u"To invoice", default=True)
    price = fields.Float(u"Price", required=True, digits=(16, 2))
    billing_period_start = fields.Date(u"Billing period start", required=True)
    billing_period_end = fields.Date(u"Billing period end", required=True)
    billed_period_start = fields.Date(u"Billed period start", required=True)
    billed_period_end = fields.Date(u"Billed period end", required=True)
    sale_recurrence_line_id = fields.Many2one('ndp.sale.recurrence.line',
                                              string=u"Sale recurrence line",
                                              related='consu_group_id.sale_recurrence_line_id')
    consu_group_id = fields.Many2one('ndp.sale.consu.group', string=u"Consumption group", required=True)
    invoice_line_id = fields.Many2one('account.invoice.line', string=u"Invoice line")
    tax_ids = fields.Many2many('account.tax', string="Taxes")

    @api.multi
    def bill_consumption_lines(self, account_invoice, wizard_date):
        vals_invoice_lines = []
        uom_unite = self.env.ref('product.product_uom_unit')
        for rec in self:
            # Une ligne de conso est toujours facturée en 'échue' et donc facturée durant la période après celle de
            # sa création.
            if rec.billing_period_start <= fields.Date.to_string(wizard_date) < rec.billing_period_end:
                vals_invoice_lines.append({
                    'invoice_id': account_invoice.id,
                    'product_id': rec.product_id.id,
                    'name': rec.name,
                    'account_id': account_invoice.account_id.id,
                    'account_analytic_id': rec.consu_group_id.ndp_analytic_contract_id.analytic_account_id.id,
                    'quantity': 1,
                    'uos_id': uom_unite.id,
                    'price_unit': rec.price,
                    'billed_period_start': rec.billed_period_start,
                    'billed_period_end': rec.billed_period_end,
                    'invoice_line_tax_id': [(6, 0, rec.tax_ids.ids)],
                    'sale_consu_line_ids': [(4, rec.id, 0)],
                })

        return vals_invoice_lines


class NdpConsuType(models.Model):
    _name = 'ndp.consu.type'

    name = fields.Char(u"Name")
    config_model = fields.Char(u"Configuration model")
    is_configurable = fields.Boolean(u"Configurable", default=False)
    product_id = fields.Many2one('product.product', string=u"Product")

    @api.model
    def default_get(self, fields_list):
        res = super(NdpConsuType, self).default_get(fields_list)
        res.update({'product_id': self.env.ref('ndp_analytic_contract.product_consu')})
        return res

    @api.model
    def _prepare_consu_line(self, line):
        return self.env['ndp.sale.consu.line']

    @api.model
    def get_consu_group_infos(self, domain):
        uom_recurrence_month = self.env.ref('ndp_analytic_contract.ndp_uom_recurrence_month')
        consu_group = self.env['ndp.sale.consu.group'].search(domain)
        sr_line = consu_group.sale_recurrence_line_id
        if sr_line:
            months_to_bill = self.env['product.uom']._compute_qty(sr_line.recurrence_id.id, 1, uom_recurrence_month.id)
        else:
            months_to_bill = self.env['product.uom']._compute_qty(
                consu_group.recurrence_id.id, 1, uom_recurrence_month.id)
        return consu_group, months_to_bill, sr_line

    @api.multi
    def open_consu_config(self, consu_group):
        """
        Permet d'accéder à un modèle de configuration.
        """
        if not self.config_model:
            return

        config = self.env[self.config_model].search([
            ('consu_type_id', '=', self.id),
            ('consu_group_id', '=', consu_group.id)
        ])

        return {
            'type': 'ir.actions.act_window',
            'name': u"Configuration",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.config_model,
            'res_id': config.id,
            'target': 'new',
        }


class NdpSaleConsuLineGroup(models.Model):
    _name = 'ndp.sale.consu.group'

    name = fields.Char(string=u"Name", related='consu_type_id.name')
    ndp_analytic_contract_id = fields.Many2one('ndp.analytic.contract', string=u"Contract", required=True)
    consu_type_id = fields.Many2one('ndp.consu.type', string=u"Consumption type", required=True)
    sale_recurrence_line_id = fields.Many2one('ndp.sale.recurrence.line',
                                              string=u"Recurrence line")
    sale_consu_line_ids = fields.One2many('ndp.sale.consu.line',
                                          'consu_group_id',
                                          string=u"Consumption lines")
    recurrence_id = fields.Many2one('product.uom', string=u"Recurrence")
    amount_expected = fields.Float(u"Expected")
    amount_invoiced = fields.Float(u"Invoiced", compute='_compute_amounts')
    amount_remaining = fields.Float(u"Remaining", compute='_compute_amounts')
    amount_to_invoice = fields.Float(u"To invoice", compute='_compute_amounts')
    is_configurable = fields.Boolean(u"Configurable", related='consu_type_id.is_configurable')

    @api.model
    def default_get(self, fields_list):
        res = super(NdpSaleConsuLineGroup, self).default_get(fields_list)
        res.update({'recurrence_id': self.env.ref('ndp_analytic_contract.ndp_uom_recurrence_month').id})
        return res

    @api.multi
    def _compute_amounts(self):
        for rec in self:
            sc_invoiced_lines = self.env['ndp.sale.consu.line'].search([
                ('consu_group_id', '=', rec.id),
                ('invoice_line_id', '!=', False)
            ])

            rec.amount_invoiced = sum(self.env['account.invoice.line'].search([
                ('id', 'in', sc_invoiced_lines.mapped('invoice_line_id').ids),
            ]).mapped('price_subtotal'))
            rec.amount_remaining = rec.amount_expected - rec.amount_invoiced
            rec.amount_to_invoice = sum(self.env['ndp.sale.consu.line'].search([
                ('consu_group_id', '=', rec.id),
                ('invoice_line_id', '=', False)
            ]).mapped('price'))

    @api.multi
    @api.onchange('sale_recurrence_line_id')
    def _onchange_for_recurrence_id(self):
        self.ensure_one()
        if self.sale_recurrence_line_id:
            self.recurrence_id = self.sale_recurrence_line_id.recurrence_id
        else:
            self.recurrence_id = self.env.ref('ndp_analytic_contract.ndp_uom_recurrence_month')

    @api.multi
    def open_consu_config(self):
        """
        Permet d'accéder au modèle de configuration du groupe de conso qui dépend de son type de conso.
        """
        self.ensure_one()
        if self.consu_type_id.is_configurable:
            return self.consu_type_id.open_consu_config(self.id)

    @api.multi
    def open_consu_line_tree(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': u"Consumption lines",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ndp.sale.consu.line',
            'target': 'current',
            'domain': [('consu_group_id.ndp_analytic_contract_id', '=', self.ndp_analytic_contract_id.id)],
            'context': {'default_consu_group_id': self.id},
        }
