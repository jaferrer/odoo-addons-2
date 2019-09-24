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


class PurchaseOrderProjectImproved(models.Model):
    _inherit = 'purchase.order'

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string=u"Compte analytique",
                                          readonly=True,
                                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    project_id = fields.Many2one('project.project',
                                 string="Projet",
                                 required=True,
                                 compute='_compute_project_id',
                                 inverse='_inverse_project_id')

    @api.multi
    def _compute_project_id(self):
        """
        Attention : Ne fonctionne PAS à la Création dans le sens analytic_account_id -> project_id.
        """
        for rec in self:
            rec.project_id = rec.analytic_account_id.project_ids[:1]

    @api.multi
    def _inverse_project_id(self):
        for rec in self:
            rec.analytic_account_id = rec.project_id.analytic_account_id

    @api.model
    def default_get(self, fields):
        """
        Permet d'assigner également un projet lorsque l'on crée une Commande d'achat depuis un Projet.
        """

        res = super(PurchaseOrderProjectImproved, self).default_get(fields)

        analytic_account_id = res.get('analytic_account_id')
        if analytic_account_id:
            project = self.env['project.project'].search([('analytic_account_id', '=', analytic_account_id)], limit=1)
            res.update({
                'project_id': project.id,
            })

        return res
