# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
#    along with this
#


import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AerooIrModelImproved(models.Model):
    _name = 'ir.model'
    _inherit = 'ir.model'

    def _add_manual_models(self):
        """
        Calls original function + loads Aeroo Reports 'location' reports
        """
        super(AerooIrModelImproved, self)._add_manual_models()
        if 'report_aeroo' in self.pool._init_modules:
            _logger.info('Adding aeroo reports location models')
            self.env.cr.execute("""SELECT report_name, name, parser_loc, id
                    FROM ir_act_report_xml WHERE
                    report_type = 'aeroo'
                    AND parser_state = 'loc'
                    ORDER BY id
                    """)
            for report in self.env.cr.dictfetchall():
                parser = self.env['ir.actions.report'].load_from_file(report['parser_loc'], report['id'])
                parser._build_model(self.pool, self.env.cr)
