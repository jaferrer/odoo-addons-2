# -*- coding: utf8 -*-
from odoo import models, fields


class TrainingSitting(models.Model):
    _inherit = 'training.sitting'

    survey_start_sitting_ids = fields.Many2many('survey.survey', 'survey_sitting_start_rel',
                                                string="Survey start sitting",
                                                domain=[('sitting_survey', '=', 'start_sitting')])
    survey_end_sitting_ids = fields.Many2many('survey.survey', 'survey_sitting_end_rel', string="Survey end sitting",
                                              domain=[('sitting_survey', '=', 'end_sitting')])
