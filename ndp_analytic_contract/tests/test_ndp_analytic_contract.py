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

from openerp.tests import common


class TestNdpAnalyticContract(common.TransactionCase):

    def setUp(self):
        super(TestNdpAnalyticContract, self).setUp()
        self.product_1 = self.browse_ref('ndp_analytic_contract.product_1')
        self.partner_1 = self.browse_ref('ndp_analytic_contract.partner_1')
        self.uom_temporality_month = self.browse_ref('ndp_analytic_contract.ndp_uom_temporalite_month')
        self.uom_temporality_trimester = self.browse_ref('ndp_analytic_contract.ndp_uom_temporalite_trimester')
        self.uom_temporality_semester = self.browse_ref('ndp_analytic_contract.ndp_uom_temporalite_semester')
        self.uom_temporality_year = self.browse_ref('ndp_analytic_contract.ndp_uom_temporalite_year')
        self.uom_recurrence_month = self.browse_ref('ndp_analytic_contract.ndp_uom_recurrence_month')
        self.uom_recurrence_trimester = self.browse_ref('ndp_analytic_contract.ndp_uom_recurrence_trimester')
        self.uom_recurrence_semester = self.browse_ref('ndp_analytic_contract.ndp_uom_recurrence_semester')
        self.uom_recurrence_year = self.browse_ref('ndp_analytic_contract.ndp_uom_recurrence_year')
        self.uom_unite = self.browse_ref('product.product_uom_unit')
        self.consu_type_1 = self.browse_ref('ndp_analytic_contract.ndp_consu_type_1')
        self.consu_type_2 = self.browse_ref('ndp_analytic_contract.ndp_consu_type_2')
        self.consu_type_3 = self.browse_ref('ndp_analytic_contract.ndp_consu_type_3')
        self.consu_type_4 = self.browse_ref('ndp_analytic_contract.ndp_consu_type_4')

    def check_recurrence_line_duplication(self, contract_sr_line, sr_line, contract):
        """
        Teste la bonne copie des lignes de récurrence dans le contrat à la confirmation d'un devis.
        """
        self.assertEqual(contract_sr_line.product_id, sr_line.product_id)
        self.assertEqual(contract_sr_line.name, sr_line.name)
        self.assertEqual(contract_sr_line.date_start, sr_line.date_start)
        self.assertEqual(contract_sr_line.billing_day, sr_line.billing_day)
        self.assertEqual(contract_sr_line.term, sr_line.term)
        self.assertEqual(contract_sr_line.calendar_type, sr_line.calendar_type)
        self.assertEqual(contract_sr_line.product_uom_id, sr_line.product_uom_id)
        self.assertEqual(contract_sr_line.product_uom_qty, sr_line.product_uom_qty)
        self.assertEqual(contract_sr_line.price_unit, sr_line.price_unit)
        self.assertEqual(contract_sr_line.recurrence_id, sr_line.recurrence_id)
        self.assertEqual(contract_sr_line.ndp_analytic_contract_id, contract)
        self.assertEqual(contract_sr_line.sale_id, self.env['sale.order'])

    def check_contract_recurrence_invoicing(self, sr_invoice_line, contract_sr_line, invoice, qty, price_subtotal,
                                            period_start, period_end):
        """
        Vérifie la bonne facturation du contrat.
        """
        self.assertEqual(sr_invoice_line.product_id, contract_sr_line.product_id)
        self.assertEqual(sr_invoice_line.name, contract_sr_line.name)
        self.assertEqual(sr_invoice_line.account_id, invoice.account_id)
        self.assertEqual(sr_invoice_line.account_analytic_id,
                         contract_sr_line.ndp_analytic_contract_id.analytic_account_id)
        self.assertAlmostEqual(sr_invoice_line.quantity, qty, delta=3)
        self.assertEqual(sr_invoice_line.uos_id, contract_sr_line.product_uom_id)
        self.assertEqual(sr_invoice_line.price_unit, contract_sr_line.price_unit)
        self.assertAlmostEqual(sr_invoice_line.price_subtotal, price_subtotal, delta=2)
        self.assertEqual(sr_invoice_line.billed_period_start, period_start)
        self.assertEqual(sr_invoice_line.billed_period_end, period_end)
        self.assertEqual(sr_invoice_line.sale_recurrence_line_ids, contract_sr_line)

    def check_contract_conso_invoicing(self, sc_invoice_line, contract_sc_line, invoice):
        """
        Vérifie la bonne facturation du contrat.
        """
        self.assertEqual(sc_invoice_line.product_id, contract_sc_line.product_id)
        self.assertEqual(sc_invoice_line.name, contract_sc_line.name)
        self.assertEqual(sc_invoice_line.account_id, invoice.account_id)
        self.assertEqual(sc_invoice_line.account_analytic_id,
                         contract_sc_line.ndp_analytic_contract_id.analytic_account_id)
        self.assertAlmostEqual(sc_invoice_line.quantity, 1, delta=3)
        self.assertEqual(sc_invoice_line.uos_id, self.uom_unite)
        self.assertEqual(sc_invoice_line.price_unit, contract_sc_line.price)
        self.assertAlmostEqual(sc_invoice_line.price_subtotal, contract_sc_line.price, delta=2)
        self.assertEqual(sc_invoice_line.billed_period_start, contract_sc_line.billed_period_start)
        self.assertEqual(sc_invoice_line.billed_period_end, contract_sc_line.billed_period_end)
        self.assertEqual(sc_invoice_line.sale_consu_line_ids, contract_sc_line)

    def test_10_ndp_analytic_contract(self):
        """
        Teste le workflow Devis -> Création de lignes récurrentes -> Confirmation -> Création du contrat -> Facturation
        du contrat. On prend en compte les situations suivantes :
        - Termes 'échu' et 'échoir'.
        - Calendirer 'Anniversaire' ou 'Civil'.
        """
        recurrence_line_triplet_list = [
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 1",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 5,
                'price_unit': 60,
                'recurrence_id': self.uom_recurrence_month.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 2",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 6,
                'price_unit': 70,
                'recurrence_id': self.uom_recurrence_trimester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 3",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 4",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 8,
                'price_unit': 90,
                'recurrence_id': self.uom_recurrence_year.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 5",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 5,
                'price_unit': 60,
                'recurrence_id': self.uom_recurrence_month.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 6",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 6,
                'price_unit': 70,
                'recurrence_id': self.uom_recurrence_trimester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 7",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 8",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 8,
                'price_unit': 90,
                'recurrence_id': self.uom_recurrence_year.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 9",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 5,
                'price_unit': 60,
                'recurrence_id': self.uom_recurrence_month.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 10",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 6,
                'price_unit': 70,
                'recurrence_id': self.uom_recurrence_trimester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 11",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 12",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 8,
                'price_unit': 90,
                'recurrence_id': self.uom_recurrence_year.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 13",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 5,
                'price_unit': 60,
                'recurrence_id': self.uom_recurrence_month.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 14",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_month.id,
                'product_uom_qty': 6,
                'price_unit': 70,
                'recurrence_id': self.uom_recurrence_trimester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 15",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 16",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 8,
                'price_unit': 90,
                'recurrence_id': self.uom_recurrence_year.id,
            }),
        ]

        sale_order = self.env['sale.order'].create({
            'name': u"Devis test",
            'partner_id': self.partner_1.id,
            'sale_recurrence_line_ids': recurrence_line_triplet_list,
        })
        self.assertTrue(sale_order)
        self.assertEqual(len(sale_order.sale_recurrence_line_ids), 16)

        for sr_line in sale_order.sale_recurrence_line_ids:
            if sr_line.name == u"Récurrente 1":
                sr_line_1 = sr_line
            elif sr_line.name == u"Récurrente 2":
                sr_line_2 = sr_line
            elif sr_line.name == u"Récurrente 3":
                sr_line_3 = sr_line
            elif sr_line.name == u"Récurrente 4":
                sr_line_4 = sr_line
            elif sr_line.name == u"Récurrente 5":
                sr_line_5 = sr_line
            elif sr_line.name == u"Récurrente 6":
                sr_line_6 = sr_line
            elif sr_line.name == u"Récurrente 7":
                sr_line_7 = sr_line
            elif sr_line.name == u"Récurrente 8":
                sr_line_8 = sr_line
            elif sr_line.name == u"Récurrente 9":
                sr_line_9 = sr_line
            elif sr_line.name == u"Récurrente 10":
                sr_line_10 = sr_line
            elif sr_line.name == u"Récurrente 11":
                sr_line_11 = sr_line
            elif sr_line.name == u"Récurrente 12":
                sr_line_12 = sr_line
            elif sr_line.name == u"Récurrente 13":
                sr_line_13 = sr_line
            elif sr_line.name == u"Récurrente 14":
                sr_line_14 = sr_line
            elif sr_line.name == u"Récurrente 15":
                sr_line_15 = sr_line
            else:
                sr_line_16 = sr_line

        # Confirmation du devis qui crée un contrat
        sale_order.action_button_confirm()
        contract = self.env['ndp.analytic.contract'].search([('analytic_account_id', '=', sale_order.project_id.id)])
        self.assertTrue(contract)
        self.assertEqual(len(contract.sale_recurrence_line_ids), 16)

        for sr_line in contract.sale_recurrence_line_ids:
            if sr_line.name == u"Récurrente 1":
                contract_sr_line_1 = sr_line
            elif sr_line.name == u"Récurrente 2":
                contract_sr_line_2 = sr_line
            elif sr_line.name == u"Récurrente 3":
                contract_sr_line_3 = sr_line
            elif sr_line.name == u"Récurrente 4":
                contract_sr_line_4 = sr_line
            elif sr_line.name == u"Récurrente 5":
                contract_sr_line_5 = sr_line
            elif sr_line.name == u"Récurrente 6":
                contract_sr_line_6 = sr_line
            elif sr_line.name == u"Récurrente 7":
                contract_sr_line_7 = sr_line
            elif sr_line.name == u"Récurrente 8":
                contract_sr_line_8 = sr_line
            elif sr_line.name == u"Récurrente 9":
                contract_sr_line_9 = sr_line
            elif sr_line.name == u"Récurrente 10":
                contract_sr_line_10 = sr_line
            elif sr_line.name == u"Récurrente 11":
                contract_sr_line_11 = sr_line
            elif sr_line.name == u"Récurrente 12":
                contract_sr_line_12 = sr_line
            elif sr_line.name == u"Récurrente 13":
                contract_sr_line_13 = sr_line
            elif sr_line.name == u"Récurrente 14":
                contract_sr_line_14 = sr_line
            elif sr_line.name == u"Récurrente 15":
                contract_sr_line_15 = sr_line
            else:
                contract_sr_line_16 = sr_line

        # On teste la bonne duplication des lignes récurrentes dans le contrat
        self.check_recurrence_line_duplication(contract_sr_line_1, sr_line_1, contract)
        self.check_recurrence_line_duplication(contract_sr_line_2, sr_line_2, contract)
        self.check_recurrence_line_duplication(contract_sr_line_3, sr_line_3, contract)
        self.check_recurrence_line_duplication(contract_sr_line_4, sr_line_4, contract)
        self.check_recurrence_line_duplication(contract_sr_line_5, sr_line_5, contract)
        self.check_recurrence_line_duplication(contract_sr_line_6, sr_line_6, contract)
        self.check_recurrence_line_duplication(contract_sr_line_7, sr_line_7, contract)
        self.check_recurrence_line_duplication(contract_sr_line_8, sr_line_8, contract)
        self.check_recurrence_line_duplication(contract_sr_line_9, sr_line_9, contract)
        self.check_recurrence_line_duplication(contract_sr_line_10, sr_line_10, contract)
        self.check_recurrence_line_duplication(contract_sr_line_11, sr_line_11, contract)
        self.check_recurrence_line_duplication(contract_sr_line_12, sr_line_12, contract)
        self.check_recurrence_line_duplication(contract_sr_line_13, sr_line_13, contract)
        self.check_recurrence_line_duplication(contract_sr_line_14, sr_line_14, contract)
        self.check_recurrence_line_duplication(contract_sr_line_15, sr_line_15, contract)
        self.check_recurrence_line_duplication(contract_sr_line_16, sr_line_16, contract)

        # Création du wizard de facturation des lignes échu
        echu_lines = self.env['ndp.sale.recurrence.line'].search([
            ('ndp_analytic_contract_id', '=', contract.id),
            ('term', '=', 'echu'),
        ])
        self.assertEqual(len(echu_lines), 8)
        wizard_1 = self.env['ndp.contract.billing.wizard'].create({
            'ndp_analytic_contract_id': contract.id,
            'billing_month': 5,
            'billing_year': 2020,
            'sale_recurrence_line_ids': [(6, 0, echu_lines.ids)],
        })
        wizard_1_view = wizard_1.contract_create_invoice()
        invoice_1 = self.env['account.invoice'].browse(wizard_1_view.get('res_id'))
        self.assertTrue(invoice_1)
        self.assertEqual(len(invoice_1.invoice_line), 8)

        for invoice_line in invoice_1.invoice_line:
            if invoice_line.name == u"Récurrente 1":
                sr_invoice_line_1 = invoice_line
            elif invoice_line.name == u"Récurrente 2":
                sr_invoice_line_2 = invoice_line
            elif invoice_line.name == u"Récurrente 3":
                sr_invoice_line_3 = invoice_line
            elif invoice_line.name == u"Récurrente 4":
                sr_invoice_line_4 = invoice_line
            elif invoice_line.name == u"Récurrente 5":
                sr_invoice_line_5 = invoice_line
            elif invoice_line.name == u"Récurrente 6":
                sr_invoice_line_6 = invoice_line
            elif invoice_line.name == u"Récurrente 7":
                sr_invoice_line_7 = invoice_line
            else:
                sr_invoice_line_8 = invoice_line

        # On teste la bonne création des lignes de facturation
        self.check_contract_recurrence_invoicing(sr_invoice_line_1, contract_sr_line_1, invoice_1, 5, 300,
                                                 u"2020-03-07", u"2020-04-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_2, contract_sr_line_2, invoice_1, 18, 1260,
                                                 u"2019-11-07", u"2020-02-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_3, contract_sr_line_3, invoice_1, 14, 1120,
                                                 u"2019-08-07", u"2020-02-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_4, contract_sr_line_4, invoice_1, 32, 2880,
                                                 u"2019-02-07", u"2020-02-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_5, contract_sr_line_5, invoice_1, 5, 300,
                                                 u"2020-04-01", u"2020-04-30")
        self.check_contract_recurrence_invoicing(sr_invoice_line_6, contract_sr_line_6, invoice_1, 18, 1260,
                                                 u"2020-01-01", u"2020-03-31")
        self.check_contract_recurrence_invoicing(sr_invoice_line_7, contract_sr_line_7, invoice_1, 14, 1120,
                                                 u"2019-07-01", u"2019-12-31")
        self.check_contract_recurrence_invoicing(sr_invoice_line_8, contract_sr_line_8, invoice_1, 28.756, 2588.05,
                                                 u"2019-02-07", u"2019-12-31")

        # Création du wizard de facturation des lignes échoir
        echoir_lines = self.env['ndp.sale.recurrence.line'].search([
            ('ndp_analytic_contract_id', '=', contract.id),
            ('term', '=', 'echoir'),
        ])
        self.assertEqual(len(echoir_lines), 8)
        wizard_2 = self.env['ndp.contract.billing.wizard'].create({
            'ndp_analytic_contract_id': contract.id,
            'billing_month': 5,
            'billing_year': 2019,
            'sale_recurrence_line_ids': [(6, 0, echoir_lines.ids)],
        })
        wizard_2_view = wizard_2.contract_create_invoice()
        invoice_2 = self.env['account.invoice'].browse(wizard_2_view.get('res_id'))
        self.assertTrue(invoice_2)
        self.assertEqual(len(invoice_2.invoice_line), 8)

        for invoice_line in invoice_2.invoice_line:
            if invoice_line.name == u"Récurrente 9":
                sr_invoice_line_9 = invoice_line
            elif invoice_line.name == u"Récurrente 10":
                sr_invoice_line_10 = invoice_line
            elif invoice_line.name == u"Récurrente 11":
                sr_invoice_line_11 = invoice_line
            elif invoice_line.name == u"Récurrente 12":
                sr_invoice_line_12 = invoice_line
            elif invoice_line.name == u"Récurrente 13":
                sr_invoice_line_13 = invoice_line
            elif invoice_line.name == u"Récurrente 14":
                sr_invoice_line_14 = invoice_line
            elif invoice_line.name == u"Récurrente 15":
                sr_invoice_line_15 = invoice_line
            else:
                sr_invoice_line_16 = invoice_line

        # On teste la bonne création des lignes de facturation
        self.check_contract_recurrence_invoicing(sr_invoice_line_9, contract_sr_line_9, invoice_2, 5, 300,
                                                 u"2019-04-07", u"2019-05-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_10, contract_sr_line_10, invoice_2, 18, 1260,
                                                 u"2019-02-07", u"2019-05-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_11, contract_sr_line_11, invoice_2, 14, 1120,
                                                 u"2019-02-07", u"2019-08-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_12, contract_sr_line_12, invoice_2, 32, 2880,
                                                 u"2019-02-07", u"2020-02-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_13, contract_sr_line_13, invoice_2, 5, 300,
                                                 u"2019-05-01", u"2019-05-31")
        self.check_contract_recurrence_invoicing(sr_invoice_line_14, contract_sr_line_14, invoice_2, 18, 1260,
                                                 u"2019-04-01", u"2019-06-30")
        self.check_contract_recurrence_invoicing(sr_invoice_line_15, contract_sr_line_15, invoice_2, 11.138, 891.04,
                                                 u"2019-02-07", u"2019-06-30")
        self.check_contract_recurrence_invoicing(sr_invoice_line_16, contract_sr_line_16, invoice_2, 28.756, 2588.04,
                                                 u"2019-02-07", u"2019-12-31")

    def test_20_ndp_analytic_contract(self):
        """
        Teste la facturation des lignes de consommation.
        """
        recurrence_line_triplet_list = [
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 3",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 7",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echu',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 11",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'birthday',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
            (0, 0, {
                'product_id': self.product_1.id,
                'name': u"Récurrente 15",
                'date_start': u"2019-02-07",
                'billing_day': 7,
                'term': 'echoir',
                'calendar_type': 'civil',
                'product_uom_id': self.uom_temporality_trimester.id,
                'product_uom_qty': 7,
                'price_unit': 80,
                'recurrence_id': self.uom_recurrence_semester.id,
            }),
        ]

        contract = self.env['ndp.analytic.contract'].create({
            'name': u"Contrat test",
            'partner_id': self.partner_1.id,
            'sale_recurrence_line_ids': recurrence_line_triplet_list,
        })
        self.assertTrue(contract)
        self.assertEqual(len(contract.sale_recurrence_line_ids), 4)

        for sr_line in contract.sale_recurrence_line_ids:
            if sr_line.name == u"Récurrente 3":
                sr_line_3 = sr_line
            elif sr_line.name == u"Récurrente 7":
                sr_line_7 = sr_line
            elif sr_line.name == u"Récurrente 11":
                sr_line_11 = sr_line
            else:
                sr_line_15 = sr_line

        for consu_group in contract.consu_group_ids:
            if consu_group.consu_type_id == self.consu_type_1:
                consu_group.sale_recurrence_line_id = sr_line_3
                consu_group_1 = consu_group
            elif consu_group.consu_type_id == self.consu_type_2:
                consu_group.sale_recurrence_line_id = sr_line_7
                consu_group_2 = consu_group
            elif consu_group.consu_type_id == self.consu_type_3:
                consu_group.sale_recurrence_line_id = sr_line_11
                consu_group_3 = consu_group
            elif consu_group.consu_type_id == self.consu_type_4:
                consu_group.sale_recurrence_line_id = sr_line_15
                consu_group_4 = consu_group

        sc_line_1 = self.env['ndp.sale.consu.line'].create({
            'consu_group_id': consu_group_1.id,
            'name': u"Consommation 1",
            'product_id': self.product_1.id,
            'date': u"2019-08-15",
            'billed_period_start': u"2019-08-07",
            'billed_period_end': u"2020-02-06",
            'billing_period_start': u"2020-02-07",
            'billing_period_end': u"2020-08-06",
            'price': 25,
        })
        sc_line_2 = self.env['ndp.sale.consu.line'].create({
            'consu_group_id': consu_group_2.id,
            'name': u"Consommation 2",
            'product_id': self.product_1.id,
            'date': u"2019-08-15",
            'billed_period_start': u"2019-08-07",
            'billed_period_end': u"2020-02-06",
            'billing_period_start': u"2020-02-07",
            'billing_period_end': u"2020-08-06",
            'price': 25,
        })
        sc_line_3 = self.env['ndp.sale.consu.line'].create({
            'consu_group_id': consu_group_3.id,
            'name': u"Consommation 3",
            'product_id': self.product_1.id,
            'date': u"2019-08-15",
            'billed_period_start': u"2019-08-07",
            'billed_period_end': u"2020-02-06",
            'billing_period_start': u"2020-02-07",
            'billing_period_end': u"2020-08-06",
            'price': 25,
        })
        sc_line_4 = self.env['ndp.sale.consu.line'].create({
            'consu_group_id': consu_group_4.id,
            'name': u"Consommation 4",
            'product_id': self.product_1.id,
            'date': u"2019-08-15",
            'billed_period_start': u"2019-08-07",
            'billed_period_end': u"2020-02-06",
            'billing_period_start': u"2020-02-07",
            'billing_period_end': u"2020-08-06",
            'price': 25,
        })

        # Création du wizard de facturation
        wizard = self.env['ndp.contract.billing.wizard'].create({
            'ndp_analytic_contract_id': contract.id,
            'billing_month': 3,
            'billing_year': 2020,
            'sale_recurrence_line_ids': [(6, 0, contract.sale_recurrence_line_ids.ids)],
            'sale_consu_line_ids': [(6, 0, contract.consu_group_ids.mapped('sale_consu_line_ids').ids)],
        })
        self.assertEqual(len(wizard.sale_recurrence_line_ids), 4)
        self.assertEqual(len(wizard.sale_consu_line_ids), 4)

        wizard_view = wizard.contract_create_invoice()
        invoice = self.env['account.invoice'].browse(wizard_view.get('res_id'))
        self.assertTrue(invoice)
        self.assertEqual(len(invoice.invoice_line), 8)

        for invoice_line in invoice.invoice_line:
            if invoice_line.name == u"Consommation 1":
                sc_invoice_line_1 = invoice_line
            elif invoice_line.name == u"Consommation 2":
                sc_invoice_line_2 = invoice_line
            elif invoice_line.name == u"Consommation 3":
                sc_invoice_line_3 = invoice_line
            elif invoice_line.name == u"Consommation 4":
                sc_invoice_line_4 = invoice_line
            elif invoice_line.name == u"Récurrente 3":
                sr_invoice_line_3 = invoice_line
            elif invoice_line.name == u"Récurrente 7":
                sr_invoice_line_7 = invoice_line
            elif invoice_line.name == u"Récurrente 11":
                sr_invoice_line_11 = invoice_line
            elif invoice_line.name == u"Récurrente 15":
                sr_invoice_line_15 = invoice_line

        # On teste la bonne création des lignes de facturation
        self.check_contract_conso_invoicing(sc_invoice_line_1, sc_line_1, invoice)
        self.check_contract_conso_invoicing(sc_invoice_line_3, sc_line_3, invoice)
        self.check_contract_conso_invoicing(sc_invoice_line_2, sc_line_2, invoice)
        self.check_contract_conso_invoicing(sc_invoice_line_4, sc_line_4, invoice)
        self.check_contract_recurrence_invoicing(sr_invoice_line_3, sr_line_3, invoice, 14, 1120,
                                                 u"2019-08-07", u"2020-02-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_7, sr_line_7, invoice, 14, 1120,
                                                 u"2019-07-01", u"2019-12-31")
        self.check_contract_recurrence_invoicing(sr_invoice_line_11, sr_line_11, invoice, 14, 1120,
                                                 u"2020-02-07", u"2020-08-06")
        self.check_contract_recurrence_invoicing(sr_invoice_line_15, sr_line_15, invoice, 14, 1120,
                                                 u"2020-01-01", u"2020-06-30")
