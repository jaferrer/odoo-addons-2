from openerp.tests import common

class TestAccountInvoiceReverse(common.TransactionCase):

    def setUp(self):
        super(TestAccountInvoiceReverse, self).setUp()
        self.invoice_0 = self.browse_ref('invoice_interco.demo_invoice_reverse_0')

    def test_1_in_to_out(self):
        """Check the reverse invoice is correct"""
        self.invoice_0.signal_workflow('invoice_open')

        reverse = self.env['account.invoice'].search([('origin', '=', self.invoice_0.number)])

        self.assertEqual(self.invoice_0.state, 'open')
        self.assertEqual('draft', reverse.state)
        self.assertEqual(self.invoice_0.company_id.partner_id, reverse.partner_id)
        self.assertEqual(self.invoice_0.partner_id, reverse.company_id.partner_id)
        self.assertEqual(self.invoice_0._inverse_type()[self.invoice_0.type], reverse.type)
        self.assertEqual(self.invoice_0.number, reverse.origin)
        self.assertFalse(reverse.move_id)
        self.assertEquals(self.invoice_0.amount_total, reverse.amount_total)
