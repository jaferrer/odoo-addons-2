# coding : utf-8
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _check_email(self):
        self.ensure_one()
        return bool(self.email)
