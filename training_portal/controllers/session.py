# -*- coding: utf-8 -*-
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo import http
from odoo.http import request


class SessionPortal(CustomerPortal):

    @http.route('/sessions', type='http', auth='user', website=True)
    def display_list_sessions(self, **kwargs):
        values = super(SessionPortal, self)._prepare_home_portal_values()
        values['sessions'] = request.env['training.session'].search([
            ('attendee_ids', 'in', request.env.user.partner_id.id),
        ])
        values['page_name'] = u"sessions"
        return request.render('training_portal.portal_sessions_list', values)

    @http.route("/session/<model('training.session'):session>", type="http", auth="user", website=True)
    def display_session(self, session, **kwargs):
        values = super(SessionPortal, self)._prepare_home_portal_values()
        values['session'] = request.env['training.session'].browse(session.id)
        values['page_name'] = 'sessions'
        return request.render('training_portal.portal_session', values)
