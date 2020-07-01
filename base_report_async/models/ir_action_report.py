# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report'

    type_multi_print = fields.Selection((
        ('file', u"Unique File"),
        ('pdf', u"Merged Pdf"),
        ('zip', u"Zip Container")
    ), u"Type container", default='file')
