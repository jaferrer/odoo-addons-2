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
from odoo import models, fields, api


class SaleOrderProjectImproved(models.Model):
    _inherit = 'sale.order'

    project_project_id = fields.Many2one('project.project',
                                         string="Project",
                                         compute='_compute_project_project_id',
                                         inverse='_inverse_project_id')

    @api.multi
    @api.onchange('project_project_id')
    def _onchange_project_id(self):
        """
        Lorsqu'on sélectionne une affaire dans un devis, les données fixes de l'affaires remplacent celles du devis.
        """

        if self.project_project_id:
            self.partner_id = self.project_project_id.partner_id.id
            self.partner_shipping_id = self.project_project_id.partner_delivery_id.id
            self.activity_id = self.project_project_id.activity_id.id
            self.activity_domain_id = self.project_project_id.activity_domain_id.id

    @api.multi
    def _compute_project_project_id(self):
        """
        Attention : Ne fonctionne pas à la Création dans le sens analytic_account_id -> project_id.
        """
        for rec in self:
            rec.project_project_id = self.env['project.project'].search(
                [('analytic_account_id', '=', rec.analytic_account_id.id)],
                limit=1
            )

    @api.multi
    def _inverse_project_id(self):

        for rec in self:
            analytic_account = self.env['account.analytic.account'].search(
                [('project_ids', 'ilike', rec.project_project_id.id)])
            rec.analytic_account_id = analytic_account

    @api.model
    def default_get(self, fields):
        """
        Permet d'assigner également un projet lorsque l'on crée un devis depuis un projet.
        """
        res = super(SaleOrderProjectImproved, self).default_get(fields)

        analytic_account_id = res.get('analytic_account_id')
        if analytic_account_id:
            project = self.env['project.project'].search([('analytic_account_id', '=', analytic_account_id)], limit=1)
            res.update({
                'project_project_id': project.id,
            })

        return res
