# -*- coding: utf8 -*-
from odoo import fields, models


class Survey(models.Model):
    _inherit = 'survey.survey'

    session_survey = fields.Selection([('start_session', u"Start of session"),
                                       ('end_session', u"End of session")], string=u"Display survey at")
