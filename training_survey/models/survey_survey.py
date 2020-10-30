# -*- coding: utf8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Survey(models.Model):
    _inherit = 'survey.survey'

    session_survey = fields.Selection([('start_session', u"Start of session"),
                                       ('end_session', u"End of session")], string=u"Display survey session at")

    sitting_survey = fields.Selection([('start_sitting', u"Start of sitting"),
                                       ('end_sitting', u"End of sitting")], string=u"Display survey sitting at")

    @api.constrains('session_survey', 'sitting_survey')
    def check_survey(self):
        for rec in self:
            if rec.session_survey and rec.sitting_survey:
                raise ValidationError(u"Survey can't be use on session and sitting in the same time.")
