# -*- coding: utf8 -*-
from odoo import fields, models


class TrainingSession(models.Model):
    _inherit = 'training.session'

    survey_start_session = fields.Many2many('survey.survey', 'survey_session_start_rel', string="Survey start session",
                                            domain=[('session_survey', '=', 'start_session')])
    survey_end_session = fields.Many2many('survey.survey', 'survey_session_end_rel', string="Survey end session",
                                          domain=[('session_survey', '=', 'end_session')])
