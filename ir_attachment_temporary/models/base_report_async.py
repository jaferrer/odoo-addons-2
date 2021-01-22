# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_temporary_report_file = fields.Boolean(string=u"Est un fichier temporaire")

    @api.model
    def _cron_delete_temporary_report_files(self):
        time_to_live = self.env['ir.config_parameter'].sudo().get_param('attachment.report.ttl', 7)
        date_to_delete = fields.Date.to_string(dt.today() + relativedelta(days=-int(time_to_live)))
        for attachment in self.search([('create_date', '<=', date_to_delete), ('is_temporary_report_file', '=', True)]):
            attachment.unlink()
