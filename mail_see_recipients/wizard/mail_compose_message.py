# coding : utf-8
from odoo import api, models


class MailComposer(models.TransientModel):
    """ Generic message composition wizard. You may inherit from this wizard
        at model and view levels to provide specific features.
    """
    _inherit = 'mail.compose.message'

    ''' overried default_get method to set default value for partner_ids and subject of mail'''

    @api.model
    def default_get(self, fields):
        result = super(MailComposer, self).default_get(fields)
        partners = self.env['res.partner'].browse(result.get('partner_ids', self.env.context.get('partner_ids', [])))
        if partners:
            result['partner_ids'] = [(6, 0, partners.filtered(lambda it: it._check_email()).ids)]
        return result
