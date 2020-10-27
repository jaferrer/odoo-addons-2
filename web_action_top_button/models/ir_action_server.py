from odoo import models, fields


class ActionTopButton(models.Model):
    _inherit = 'ir.actions.server'

    position = fields.Selection([
        ('top_button', 'Top Button'),
        ('none', 'None'),
    ], u"Position")
