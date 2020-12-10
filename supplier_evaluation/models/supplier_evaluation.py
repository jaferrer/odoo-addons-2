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


class PurchaseSupplierEvaluation(models.Model):
    _name = 'purchase.supplier.evaluation'
    _description = "Question sur la qualité du fournisseur"
    _order = 'sequence asc'

    sequence = fields.Integer(related='eval_question_id.sequence', readonly=True)
    purchase_id = fields.Many2one('purchase.order', "Commande d'achat", required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', "Fournisseur", related='purchase_id.partner_id', readonly=True)
    eval_question_id = fields.Many2one('purchase.supplier.evaluation.question', string="Question", readonly=True)
    eval_answer_id = fields.Many2one('purchase.supplier.evaluation.answer', string="Réponse")
    comment = fields.Text("Commentaire")
    grade = fields.Float("Note fournisseur", related='eval_answer_id.grade', readonly=True, group_operator='sum')
    grade_fournisseur = fields.Float("Note fournisseur", compute='_compute_grade_fournisseur')

    @api.multi
    def _compute_grade_fournisseur(self):
        for rec in self:
            rec.grade_fournisseur = sum(self.env['purchase.supplier.evaluation'].search([
                ('purchase_id', '=', rec.purchase_id.id)
            ]).mapped('grade'))


class PurchaseSupplierEvaluationQuestion(models.Model):
    _name = 'purchase.supplier.evaluation.question'
    _description = "Question sur la qualité du fournisseur"
    _order = 'sequence asc'

    name = fields.Char("Question", required=True)
    sequence = fields.Integer("Séquence")
    eval_answer_ids = fields.One2many('purchase.supplier.evaluation.answer',
                                      'eval_question_id',
                                      string="Réponses possibles")


class PurchaseSupplierEvaluationAnswer(models.Model):
    _name = 'purchase.supplier.evaluation.answer'
    _description = "Réponse à une question sur la qualité du fournisseur"
    _order = 'sequence asc'

    name = fields.Char("Réponse", required=True)
    sequence = fields.Integer("Séquence")
    grade = fields.Float("Note", default=0.0)
    eval_question_id = fields.Many2one('purchase.supplier.evaluation.question', string="Question")


class PurchaseSupplierEvaluationPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    evaluation_fournisseur_grade = fields.Float("Note du fournisseur", compute='_compute_evaluation_fournisseur_grade')

    @api.multi
    def _compute_evaluation_fournisseur_grade(self):
        for rec in self:
            rec.evaluation_fournisseur_grade = sum(self.env['purchase.supplier.evaluation'].search([
                ('purchase_id', '=', rec.id)
            ]).mapped('grade'))

    @api.multi
    def associated_evaluation_fournisseur(self):
        """Évaluation fournisseur associée à la demande d'achat."""
        self.ensure_one()

        # Création de la grille d'évaluation fournisseur pour cette demande d'achat
        if not self.env['purchase.supplier.evaluation'].search([('purchase_id', '=', self.id)]):
            eval_questions = self.env['purchase.supplier.evaluation.question'].search([])
            for question in eval_questions:
                # A supplier always have the best grade by default
                best_grade_answer = self.env['purchase.supplier.evaluation.answer']
                for answer in question.eval_answer_ids:
                    if answer.grade > best_grade_answer.grade:
                        best_grade_answer = answer
                self.env['purchase.supplier.evaluation'].create({
                    'purchase_id': self.id,
                    'eval_question_id': question.id,
                    'eval_answer_id': best_grade_answer.id,
                })

        action_ref = self.env.ref('supplier_evaluation.purchase_supplier_evaluation_action')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('purchase_id', '=', self.id)]
        action_data['context'] = {'default_purchase_id': self.id}
        return action_data
