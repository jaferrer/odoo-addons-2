# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import logging
import werkzeug
import werkzeug.urls
import werkzeug.utils

import requests

from openerp import fields, models, api, exceptions, http
from openerp.http import request

_logger = logging.getLogger(__name__)


def check_response(response):
    """Checks the given HTTP response and raise an Odoo UserError in case of exception."""
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        _logger.error("GitLab request error: %s", e.message)
        raise exceptions.UserError(e)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    gitlab_url = fields.Char("Gitlab URL", help="Enter your gitlab server URL. E.g. https://gitlab.example.com")
    gitlab_api_token = fields.Char("GitLab API Token", groups="project.group_project_manager")
    gitlab_project_id = fields.Many2one('project.gitlab.project', "GitLab Project")
    gitlab_id = fields.Integer("GitLab Project ID", related='gitlab_project_id.gitlab_id', readonly=True, store=True,
                               index=True)
    gitlab_integrated = fields.Boolean("GitLab is configured", readonly=True)

    @api.multi
    def update_gitlab_projects(self):
        """Updates the list of GitLab projects"""
        self.ensure_one()
        if not self.gitlab_url:
            raise exceptions.UserError("GitLab URL must be filled before loading GitLab Projects")
        self.env['project.gitlab.project'].load_gitlab_projects(self.gitlab_url, self.gitlab_api_token)

    @api.multi
    def setup_gitlab_integration(self):
        """Set up the 'Custom Issue Tracker' service in GitLab through API."""
        self.ensure_one()
        if not self.gitlab_url or not self.gitlab_id:
            raise exceptions.UserError(
                "GitLab URL must be filled and GitLab project must be selected before setting up integration"
            )
        url = "%s/api/v3/projects/%s/services/custom-issue-tracker" % (self.gitlab_url, self.gitlab_id)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if not base_url:
            raise exceptions.UserError(
                "'web.base.url' key must be filled in 'ir.config_parameters' table"
            )
        res = requests.put(url, data={
            'private_token': self.gitlab_api_token,
            'new_issue_url': "%s/projects/%s/issues/new" % (base_url, self.id),
            'issues_url': "%s/projects/%s/issues/:id" % (base_url, self.id),
            'project_url': "%s/projects/%s" % (base_url, self.id),
            'title': "Odoo Issue Tracker",
            'description': "This is the integration service with the Odoo Issue Tracker. "
                           "Do not modify the data in this page, but use project configuration in Odoo.",
        })
        check_response(res)
        self.gitlab_integrated = True

    @api.multi
    def remove_gitlab_integration(self):
        """Set up the 'Custom Issue Tracker' service in GitLab through API."""
        self.ensure_one()
        if not self.gitlab_url or not self.gitlab_id:
            raise exceptions.UserError(
                "GitLab URL must be filled and GitLab project must be selected before removing integration"
            )
        url = "%s/api/v3/projects/%s/services/custom-issue-tracker?private_token=%s" % (self.gitlab_url, self.gitlab_id,
                                                                                        self.gitlab_api_token)
        res = requests.delete(url)
        check_response(res)
        self.gitlab_integrated = False


class GitLabProject(models.Model):
    _name = 'project.gitlab.project'

    name = fields.Char("GitLab Project Path", index=True)
    gitlab_id = fields.Integer("GitLab Project ID")

    @api.model
    def load_gitlab_projects(self, gitlab_url, api_token):
        """Updates the list of GitLab projects with the given url and api token.

        New projects will be added, but old ones will not be deleted since they may
        only not be visible with the given api_token."""
        url = "%s/api/v3/projects" % gitlab_url
        res = requests.get(url, params={'private_token': api_token})
        check_response(res)
        projects = res.json()
        existing_project_names = [p.name for p in self.search([])]
        for proj in projects:
            if not proj['path_with_namespace'] in existing_project_names:
                self.create({
                    'name': proj['path_with_namespace'],
                    'gitlab_id': proj['id'],
                })


class ProjectTask(models.Model):
    _inherit = 'project.task'

    gitlab_issue_id = fields.Integer("GitLab Issue ID", compute="_compute_gitlab_issue_id", store=True,
                                     help="This is a unique ID across issues and tasks to link with GitLab")
    gitlab_integrated = fields.Boolean(related='project_id.gitlab_integrated', readonly=True)

    @api.multi
    @api.depends('name')
    def _compute_gitlab_issue_id(self):
        for rec in self:
            rec.gitlab_issue_id = rec.id and 2 * rec.id or False


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    gitlab_issue_id = fields.Integer("GitLab Issue ID", compute="_compute_gitlab_issue_id", store=True,
                                     help="This is a unique ID across issues and tasks to link with GitLab")
    gitlab_integrated = fields.Boolean(related='project_id.gitlab_integrated', readonly=True)

    @api.multi
    @api.depends('name')
    def _compute_gitlab_issue_id(self):
        for rec in self:
            rec.gitlab_issue_id = rec.id and 2 * rec.id + 1 or False


class ProjectGitLabController(http.Controller):
    @http.route("/projects/<project_id>", type="http", auth="none")
    def project(self, project_id):
        tasks_action = request.env.ref('project.act_project_project_2_project_task_all')
        url = "/web#%s" % werkzeug.urls.url_encode({
            'active_id': project_id,
            'view_type': 'list',
            'model': 'project_task',
            'action': tasks_action.id,
        })
        return werkzeug.utils.redirect(url)

    @http.route("/projects/<project_id>/issues/<issue_id>", type="http", auth="public")
    def project_issue(self, project_id, issue_id):
        query_hash = {
            'active_id': project_id,
            'view_type': 'form',
        }
        task = request.env['project.task'].search([('gitlab_issue_id', '=', issue_id)])
        if task:
            query_hash['action'] = request.env.ref('project.act_project_project_2_project_task_all').id
            query_hash['model'] = 'project_task'
            query_hash['id'] = task.id
        else:
            issue = request.env['project.issue'].search([('gitlab_issue_id', '=', issue_id)])
            if issue:
                query_hash['action'] = request.env.ref('project_issue.act_project_project_2_project_issue_all').id
                query_hash['model'] = 'project_issue'
                query_hash['id'] = issue.id
            else:
                return http.local_redirect("/project/%s" % project_id)
        url = "/web#%s" % werkzeug.urls.url_encode(query_hash)
        return werkzeug.utils.redirect(url)

    @http.route("/projects/<project_id>/issues/new", type="http", auth="none")
    def project_issue_new(self, project_id):
        query_hash = {
            'action': request.env.ref('project.act_project_project_2_project_task_all').id,
            'model': 'project_task',
            'active_id': project_id,
            'view_type': 'form',
        }
        url = "/web#%s" % werkzeug.urls.url_encode(query_hash)
        return werkzeug.utils.redirect(url)
