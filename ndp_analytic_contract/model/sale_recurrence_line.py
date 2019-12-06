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
import datetime

from dateutil import relativedelta

from openerp import models, fields, api
from openerp.tools import float_round


class NdpSaleRecurrenceLine(models.Model):
    _name = 'ndp.sale.recurrence.line'

    product_id = fields.Many2one('product.product', string=u"Service", required=True, domain=[('type', '=', 'service')])
    name = fields.Char(u"Description")
    date_start = fields.Date(u"Start date", required=True)
    date_end = fields.Date(u"End date")
    billing_day = fields.Selection([
        (1, u"1"), (2, u"2"), (3, u"3"), (4, u"4"), (5, u"5"), (6, u"6"), (7, u"7"), (8, u"8"),
        (9, u"9"), (10, u"10"), (11, u"11"), (12, u"12"), (13, u"13"), (14, u"14"), (15, u"15"),
        (16, u"16"), (17, u"17"), (18, u"18"), (19, u"19"), (20, u"20"), (21, u"21"), (22, u"22"),
        (23, u"23"), (24, u"24"), (25, u"25"), (26, u"26"), (27, u"27"), (28, u"28"), (29, u"29"),
        (30, u"30"), (31, u"31")],
        string=u"Day of billing",
        required=True)
    next_billing_date = fields.Date(u"Next billing date", readonly=True)
    true_nbdate = fields.Date(u"Next billing date", compute='_compute_true_nbdate', store=True)
    term = fields.Selection([('echu', u"Échu"), ('echoir', u"Échoir")], string=u"Term", required=True)
    calendar_type = fields.Selection([('civil', u"Civil"), ('birthday', u"Birthday")],
                                     string=u"Calendar type",
                                     required=True)
    product_uom_id = fields.Many2one('product.uom', string=u"Unit", required=True)
    product_uom_qty = fields.Float(u"Quantity", required=True, digits=(16, 3))
    price_unit = fields.Float(u"Unit price", required=True, digits=(16, 2))
    recurrence_id = fields.Many2one('product.uom', string=u"Recurrence", required=True)
    tax_ids = fields.Many2many('account.tax', string="Taxes")
    sale_id = fields.Many2one('sale.order', string=u"Sale order")
    sale_id_state = fields.Selection(related='sale_id.state', string=u"État de la commande")
    ndp_analytic_contract_id = fields.Many2one('ndp.analytic.contract', string=u"Contract")
    analytic_contract_state = fields.Selection(related='ndp_analytic_contract_id.state', string=u"État du contrat")
    auto_invoice = fields.Boolean(u"To invoice", default=True)
    product_categ_id = fields.Many2one('product.category',
                                       string=u"Service type",
                                       related='product_id.categ_id',
                                       readonly=True)
    standard_price = fields.Float(u"Cost price", readonly=True, related='product_id.standard_price')

    @api.multi
    @api.onchange('date_start', 'calendar_type')
    def _onchange_for_billing_day(self):
        self.ensure_one()
        if self.calendar_type == 'civil':
            self.billing_day = 1
        else:
            self.billing_day = self.date_start and fields.Date.from_string(self.date_start).day or False

    @api.multi
    @api.onchange('date_start')
    def _onchange_for_date_end(self):
        self.ensure_one()
        if self.date_start:
            date_start_datetime = fields.Date.from_string(self.date_start)
            self.date_end = fields.Date.to_string(date_start_datetime + relativedelta.relativedelta(years=1))
        else:
            self.date_end = False

    @api.multi
    @api.depends('next_billing_date', 'billing_day')
    def _compute_true_nbdate(self):
        """
        Permet de décaler le next_billing_day en fonction du jour du mois sélectionné pour le cron de facturation.
        """
        for rec in self:
            next_billing_date = rec.next_billing_date or self._origin.next_billing_date
            if next_billing_date:
                next_billing_month = fields.Date.from_string(next_billing_date).month
                next_billing_year = fields.Date.from_string(next_billing_date).year
                true_nbdate = datetime.date(next_billing_year, next_billing_month, 1)
                rec.true_nbdate = fields.Date.to_string(true_nbdate + relativedelta.relativedelta(day=rec.billing_day))
            else:
                rec.true_nbdate = False

    @api.multi
    def get_line_period(self, wizard_date, months_to_bill):
        self.ensure_one()
        ref_date = self.next_billing_date or self.date_start
        ref_date = fields.Date.from_string(ref_date)
        nbd_day = ref_date.day
        if ref_date < wizard_date:
            while (ref_date + relativedelta.relativedelta(months=int(months_to_bill), day=nbd_day)) < wizard_date:
                ref_date += relativedelta.relativedelta(months=int(months_to_bill), day=nbd_day)
        else:
            while ref_date >= wizard_date:
                ref_date -= relativedelta.relativedelta(months=int(months_to_bill), day=nbd_day)

        return ref_date, nbd_day

    @api.multi
    def get_birthday_line_period(self, wizard_date, months_to_bill):
        """
        Récupère la date de début et de fin d'une ligne de facture provenant d'une ligne récurrente avec un calendrier
        de facturation de type 'anniversaire'.
        """
        self.ensure_one()
        period_start_day, nbd_day = self.get_line_period(wizard_date, months_to_bill)
        # Échu = période précédente de la période actuelle
        if self.term == 'echu':
            period_start_day -= relativedelta.relativedelta(months=int(months_to_bill), day=nbd_day)
        billed_period_start = fields.Date.to_string(period_start_day)
        billed_period_end = fields.Date.to_string(
            period_start_day + relativedelta.relativedelta(months=int(months_to_bill), days=-1))

        return billed_period_start, billed_period_end

    @api.model
    def get_civil_line_period(self, civil_year_start, date_to_compare, months_to_bill):
        """
        Récupère les dates de début et de fin de facturation de la période pour une ligne civile en cours de contrat.
        """
        civil_billing_date = civil_year_start
        while civil_billing_date < date_to_compare:
            civil_billing_date += relativedelta.relativedelta(months=int(months_to_bill))
        billed_period_start = fields.Date.to_string(
            civil_billing_date - relativedelta.relativedelta(months=int(months_to_bill)))
        billed_period_end = fields.Date.to_string(civil_billing_date - relativedelta.relativedelta(days=1))

        return billed_period_start, billed_period_end

    @api.model
    def get_civil_line_first_billing_date(self, recurrence_date_start, months_to_bill):
        """
        Récupère la première date de période de facturation d'un objet provenant d'un objet récurrent avec un
        calendrier de facturation de type 'civil' (Ligne récurrente, Groupe de consommation).
        """
        first_billing_date = datetime.date(recurrence_date_start.year, 1, 1)
        start_billing_period_date = first_billing_date
        while first_billing_date < recurrence_date_start:
            start_billing_period_date = first_billing_date
            first_billing_date += relativedelta.relativedelta(months=int(months_to_bill), days=-1)

        return first_billing_date, start_billing_period_date

    @api.multi
    def bill_recurrence_lines(self, account_invoice, wizard_date):
        """
        Lance le calcul de la période facturée et de la quantité. On conserve l'unité et le prix unitaire de la ligne
        récurrence. Créée les lignes de factures correspondantes.
        """
        recurrence_vals_list = []
        uom_recurrence_month = self.env.ref('ndp_analytic_contract.ndp_uom_recurrence_month')
        uom_temporality_month = self.env.ref('ndp_analytic_contract.ndp_uom_temporalite_month')
        categ_temporality = self.env.ref('ndp_analytic_contract.product_uom_categ_temporality')
        for rec in self:
            previous_period_date = False
            # On récupère la quantité d'article par mois à facturer
            if rec.product_uom_id.category_id == categ_temporality:
                uom_in_month = self.env['product.uom']._compute_qty(rec.product_uom_id.id, 1, uom_temporality_month.id)
            else:
                uom_in_month = 1.0

            # On récupère la quantité de mois à facturer
            months_to_bill = self.env['product.uom']._compute_qty(rec.recurrence_id.id, 1, uom_recurrence_month.id)

            # On cherche juste les dates de début et de fin de la période facturée
            if rec.calendar_type == 'birthday':
                billed_period_start, billed_period_end = rec.get_birthday_line_period(wizard_date, months_to_bill)

            # On récupère la fraction de récurrence à facturer pour la première période civile et les dates de début et
            # de fin de la période facturée
            else:
                # On récupère la prochaine date de facturation civile
                civil_year_start = datetime.date(wizard_date.year, 1, 1)
                recurrence_date_start = fields.Date.from_string(rec.date_start)
                first_billing_date, start_billing_period_date = self.get_civil_line_first_billing_date(
                    recurrence_date_start, months_to_bill)

                # Échoir = période en cours
                if rec.term == 'echoir':
                    # Si la date demandé est dans la première période d'abonnement
                    if recurrence_date_start <= wizard_date <= first_billing_date:
                        delta_days = float((first_billing_date - recurrence_date_start).days + 1)
                        period_days = float((first_billing_date - start_billing_period_date).days + 1)
                        months_to_bill = period_days and (delta_days / period_days) * months_to_bill or months_to_bill
                        billed_period_start = rec.date_start
                        billed_period_end = fields.Date.to_string(first_billing_date)
                    else:
                        billed_period_start, billed_period_end = self.get_civil_line_period(civil_year_start,
                                                                                            wizard_date,
                                                                                            months_to_bill)
                # Échu = période précédente
                else:
                    previous_period_date = wizard_date - relativedelta.relativedelta(months=int(months_to_bill))
                    if previous_period_date <= first_billing_date:
                        delta_days = float((first_billing_date - recurrence_date_start).days + 1)
                        period_days = float((first_billing_date - start_billing_period_date).days + 1)
                        months_to_bill = period_days and (delta_days / period_days) * months_to_bill or months_to_bill
                        billed_period_start = rec.date_start
                        billed_period_end = fields.Date.to_string(first_billing_date)
                    else:
                        billed_period_start, billed_period_end = self.get_civil_line_period(civil_year_start,
                                                                                            previous_period_date,
                                                                                            months_to_bill)

            # On ne facture pas les périodes avant la date de début de contrat
            period_date_start = fields.Date.to_string(previous_period_date) or billed_period_start
            if period_date_start < rec.date_start:
                continue

            if self.env.context.get('cron_invoice_ndp_contracts'):
                rec.next_billing_date = fields.Date.to_string(fields.Date.from_string(
                    billed_period_end) + relativedelta.relativedelta(months=int(months_to_bill), days=1))

            qty_to_bill = float_round(rec.product_uom_qty * months_to_bill / uom_in_month, 3)
            name = rec.name or rec.product_id.name
            recurrence_vals_list.append({
                'invoice_id': account_invoice.id,
                'product_id': rec.product_id.id,
                'name': name,
                'account_id': account_invoice.account_id.id,
                'account_analytic_id': rec.ndp_analytic_contract_id.analytic_account_id.id,
                'quantity': qty_to_bill,
                'uos_id': rec.product_uom_id.id,
                'price_unit': rec.price_unit,
                'billed_period_start': billed_period_start,
                'billed_period_end': billed_period_end,
                'invoice_line_tax_id': [(6, 0, rec.tax_ids.ids)],
                'sale_recurrence_line_ids': [(4, rec.id, 0)],
            })

        return recurrence_vals_list

    @api.model
    def get_next_billing_date(self, uom_recurrence_id, date_start_str, calendar_type):
        date_start = fields.Date.from_string(date_start_str)
        uom_recurrence_month = self.env.ref('ndp_analytic_contract.ndp_uom_recurrence_month')
        months_to_bill = self.env['product.uom']._compute_qty(uom_recurrence_id, 1, uom_recurrence_month.id)
        if calendar_type == 'birthday':
            next_billing_date = date_start + relativedelta.relativedelta(months=int(months_to_bill), day=date_start.day)
        else:
            civil_year_start = datetime.date(date_start.year, 1, 1)
            next_billing_date = date_start
            while civil_year_start < next_billing_date:
                civil_year_start += relativedelta.relativedelta(months=int(months_to_bill), day=1)
            next_billing_date = civil_year_start

        return fields.Date.to_string(next_billing_date)

    @api.model
    def create(self, vals):
        """
        Calcule la première date de fin de période à la création de la ligne récurrente.
        """
        vals['next_billing_date'] = self.get_next_billing_date(vals.get('recurrence_id'),
                                                               vals.get('date_start'),
                                                               vals.get('calendar_type'))
        return super(NdpSaleRecurrenceLine, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(NdpSaleRecurrenceLine, self).write(vals)

        # Met à jour la prochaine date de facturation à la mise à jour de la date de début de contrat
        if vals.get('date_start'):
            for rec in self:
                rec.next_billing_date = self.get_next_billing_date(rec.recurrence_id.id,
                                                                   rec.date_start,
                                                                   rec.calendar_type)
                if rec.next_billing_date > rec.date_end:
                    rec.auto_invoice = False
        # Lors de la dernière facturation du cron avant la fin du contrat, on arrête la facturation automatique des
        # lignes récurrentes.
        else:
            for rec in self:
                if vals.get('next_billing_date') and vals.get('next_billing_date') > rec.date_end:
                    rec.auto_invoice = False

        return res

    @api.multi
    def open_recurrence_line_form(self):
        self.ensure_one()
        return {
            'name': u"%s" % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ndp.sale.recurrence.line',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context,
        }

    @api.multi
    def dummy_save(self):
        """Bouton juste pour lancer le write"""
        pass
