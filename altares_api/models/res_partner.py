# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api
from odoo.addons.queue_job.job import job
from odoo.exceptions import UserError


class ResPartnerAltares(models.Model):
    _inherit = 'res.partner'

    altares_duns_number = fields.Char("DUNS number", readonly=True)
    viability_rating = fields.Char("Viability rating", readonly=True)
    viability_score = fields.Char("Viability score", readonly=True)
    portfolio_comparison = fields.Char("Portfolio comparison", readonly=True)
    data_depth_indicator = fields.Text("Data depth indicator", readonly=True)
    company_profile = fields.Text("Company profile", readonly=True)

    @api.multi
    def launch_altares_api_wizard(self):
        altares_api_wizard = self.env['altares.api.wizard'].create({'partner_ids': [(6, 0, self.ids)]})
        altares_api_wizard.do_update_altares_grades()

    @api.multi
    def get_altares_grade(self):
        """
        Action server.
        """
        companies = self.filtered(lambda x: x.is_company)
        companies.launch_altares_api_wizard()

    @api.model
    def create(self, vals):
        res = super().create(vals)

        # At society creation, gets its Altares grade.
        if vals.get('is_company'):
            try:
                res.launch_altares_api_wizard()
            except UserError:
                pass

        return res

    @job
    @api.multi
    def job_altares_grades_update(self):
        self.launch_altares_api_wizard()
        return "Fin de la synchronisation."

    @api.model
    def cron_launch_altares_grades_update(self, jobify=True):
        """
        Cron to update all companies Altares viability grade.
        """
        chunk_number = 0
        partners = self.env['res.partner'].search([('is_company', '=', True)])
        while partners:
            chunk_number += 1
            chunk_partners = partners[:50]
            partners = partners[50:]
            if not jobify:
                chunk_partners.job_altares_grades_update()
            else:
                chunk_partners.with_delay(
                    description="Mise à jour des notes Altares dans les sociétés (chunk %s)" % chunk_number,
                    max_retries=0
                ).job_altares_grades_update()
