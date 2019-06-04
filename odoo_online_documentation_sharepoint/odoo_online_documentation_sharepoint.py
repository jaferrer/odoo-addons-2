# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import urllib
import requests
import json

from openerp import models, fields, api, _
from openerp.addons.connector.queue.job import job
from openerp.exceptions import Warning as UserError
from openerp.addons.connector.session import ConnectorSession


@job(default_channel='root')
def job_get_refresh_token(session, model_name, context):
    """
    Job to get refresh the refresh token.
    """

    session.env[model_name].with_context(context).ropc_button_get_auth_code_sharepoint()
    return "End update"


@job(default_channel='root')
def job_scan_sharepoint_folders(session, folder_ids, context):
    """
    Job to update selected sharepoint folders during the night.
    """

    session.env['explore.sharepoint.folders'].with_context(context).browse(folder_ids).get_files_from_root()
    return "End update"


class OdooOnlineDocumentationSharepoint(models.Model):
    _inherit = 'odoo.online.documentation'

    nature = fields.Selection(selection_add=[('sharepoint', _(u"sharepoint"))])

    @api.multi
    def open_documentation(self):
        """
        Function called to open a sharepoint document.
        """

        for rec in self:
            if rec.nature == u"sharepoint":
                file_url = self.path
                url = "https://sirail.sharepoint.com/" + file_url
                return {
                    "type": "ir.actions.act_url",
                    "url": url,
                    "target": "new"
                }

            else:
                return super(OdooOnlineDocumentationSharepoint, rec).open_documentation()


class ExploreSharepointFolders(models.Model):
    _name = 'explore.sharepoint.folders'

    name = fields.Char(u"Folder's name", default=u"Documents partages", readonly=True)
    path = fields.Char(u"Path", default=u"/Documents partages", readonly=True)
    parent_id = fields.Many2one('explore.sharepoint.folders', u"Parent folder", default=u"/", readonly=True)
    children_ids = fields.One2many('explore.sharepoint.folders', 'parent_id', u"Son folders", readonly=True)
    scannable = fields.Boolean(u"To scan", default=False)

    _sql_constraints = [('path_unique_per_folder', 'unique(path)',
                         _(u"You cannot have twice the same folder."))]

    @api.multi
    def access_sharepoint(self):
        """
        Access to Sharepoint via OAuth2 method.
        """

        session = requests.Session()
        access_token = self.env['knowledge.config.settings'].get_token()
        if access_token:
            authorization = u"Bearer " + access_token
        else:
            raise UserError(_(u"No access token, please check your access to Sharepoint."))

        session.headers.update({
            'Authorization': authorization,
            'accept': u"application/json;",
        })

        return session

    @api.multi
    def get_subdirectories(self, session, current_path=None):
        """
        Function to get access to the son folders of the current folder.
        """

        if not current_path:
            current_path = self.path

        # Pour les documents avec un '.
        current_path = current_path.rstrip('/').replace("'", "''")
        full_url = """https://sirail.sharepoint.com/_api/web/GetFolderByServerRelativeUrl('%s')/Folders""" % \
                   current_path
        ans = session.get(full_url)
        if ans.status_code != 200:
            raise UserError(_(u"HTTP Request returned a %d error" % ans.status_code))
        return [{'final_path': current_path + '/' + d['Name'], 'name': d['Name']} for d in ans.json()['value']]

    @api.multi
    def explore_step_by_step(self):
        """
        Function to load son folders only when the user ask it, so we don't have to load all the data at once.
        """

        self.ensure_one()
        session = self.access_sharepoint()
        folders_info = self.get_subdirectories(session)

        for dico in folders_info:
            if dico['name'] not in self.children_ids.mapped('name'):
                self.create({'name': dico['name'],
                             'path': dico['final_path'],
                             'parent_id': self.id,
                             })
        # Màj des dossiers supprimés dans sharepoint
        old_folders_path = [d['final_path'] for d in folders_info]
        for rec in self.children_ids:
            if rec.path not in old_folders_path:
                rec.unlink()

    @api.multi
    def get_files(self, sess, file_path=None):
        """
        Function to get all files in a given folder (crush the previous files with the same name).
        """

        self.ensure_one()
        current_path = file_path or self.path
        # Pour les documents avec un '.
        current_path = current_path.rstrip('/').replace("'", "''")
        full_url = """https://sirail.sharepoint.com/_api/web/GetFolderByServerRelativeUrl('%s')/Files""" % current_path
        ans = sess.get(full_url)

        if ans.status_code != 200:
            raise UserError(_(u"HTTP Request returned a %d error" % ans.status_code))
        file_data = [{'file_path': current_path + '/' + d['Name'], 'name': d['Name']} for d in ans.json()['value']]
        # Variable pour s'assurer de ne pas charger deux fois le même fichier.
        all_files_names = self.env['odoo.online.documentation'].search([]).mapped('name')
        for data in file_data:
            if data['name'] not in all_files_names:
                self.env['odoo.online.documentation'].create({'name': data['name'],
                                                              'path': data['file_path'],
                                                              'nature': u"sharepoint",
                                                              })

    @api.multi
    def get_files_from_root(self):
        """
        Function to recursively get all files from all folders starting from a given 'root' folder.
        """

        session = self.access_sharepoint()

        for rec in self:
            root = rec.path
            stack = [root]
            while stack:
                # la valeur .pop est enlevée de stack est mise dans cur_dir
                current_dir = stack.pop()
                subdirs = [d['final_path'] for d in rec.get_subdirectories(session, current_dir)]
                stack += subdirs
                rec.get_files(session, current_dir)

    @api.model
    def folders_to_scan(self, jobify=True):
        """
        Cron to split the job between group of 100 folders.
        """

        folders = self.search([('scannable', '=', True)])
        if not jobify:
            return folders.get_files()

        while folders:
            chunk_folders = folders[:100]
            job_scan_sharepoint_folders.delay(ConnectorSession.from_env(self.env), chunk_folders.ids,
                                              dict(self.env.context))
            folders = folders[100:]

    @api.multi
    def open_folder(self):
        """
        Function linked to a button to open the folder in tree view.
        """

        return {
            'type': 'ir.actions.act_window',
            'name': _(u"Open folder"),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'explore.sharepoint.folders',
            'res_id': self.id,
            'target': 'current',
        }


class SharepointAccessIdConfig(models.TransientModel):
    _inherit = 'knowledge.config.settings'

    username_sharepoint = fields.Char(u"Username")
    password_sharepoint = fields.Char(u"Password")
    auth_code_url_sharepoint = fields.Char(u"Authentication url")

    @api.model
    def get_default_username_sharepoint(self, fields):
        username_sharepoint = self.env['ir.config_parameter']. \
            get_param('odoo_online_documentation_sharepoint.username_sharepoint')
        return {'username_sharepoint': username_sharepoint}

    @api.multi
    def set_username_sharepoint(self):
        config_parameters = self.env["ir.config_parameter"]
        for rec in self:
            config_parameters. \
                set_param("odoo_online_documentation_sharepoint.username_sharepoint", rec.username_sharepoint)

    @api.model
    def get_default_password_sharepoint(self, fields):
        password_sharepoint = self.env['ir.config_parameter']. \
            get_param('odoo_online_documentation_sharepoint.password_sharepoint')
        return {'password_sharepoint': password_sharepoint}

    @api.multi
    def set_password_sharepoint(self):
        config_parameters = self.env["ir.config_parameter"]
        for rec in self:
            config_parameters. \
                set_param("odoo_online_documentation_sharepoint.password_sharepoint", rec.password_sharepoint)

    @api.model
    def get_default_auth_code_url_sharepoint(self, fields):
        auth_code_url_sharepoint = self.env['ir.config_parameter']. \
            get_param('odoo_online_documentation_sharepoint.auth_code_url_sharepoint')
        return {'auth_code_url_sharepoint': auth_code_url_sharepoint}

    @api.multi
    def set_auth_code_url_sharepoint(self):
        config_parameters = self.env["ir.config_parameter"]
        for rec in self:
            config_parameters. \
                set_param('odoo_online_documentation_sharepoint.auth_code_url_sharepoint', rec.auth_code_url_sharepoint)

    @api.multi
    def ropc_button_get_auth_code_sharepoint(self):
        """
        Getting refresh_token without having to log in. Second proposition less secured but can be done by a cron.
        """

        config_parameters = self.env['ir.config_parameter']
        username = \
            self.env['knowledge.config.settings'].get_default_username_sharepoint(fields=None)['username_sharepoint']
        password = \
            self.env['knowledge.config.settings'].get_default_password_sharepoint(fields=None)['password_sharepoint']
        base_url = self.env['knowledge.config.settings']\
            .get_default_auth_code_url_sharepoint(fields=None)['auth_code_url_sharepoint']

        data = {
            'client_id': u"67e8fd34-23ba-4806-8e15-35a6568b4da3",
            'scope': u"openid offline_access https://sirail.sharepoint.com/user.read",
            'username': username,
            'password': password,
            'grant_type': u"password",
            'client_secret': u"Q:>QIg|I>+cE#&Vv:&=(5+ld{q[_LF%@o!=};{c1#3)",
        }

        url = base_url + u"/organizations/oauth2/v2.0/token?"

        request_token = requests.post(url, data=data)
        token_dico = request_token.json()

        vals = {}
        vals['sharepoint_refresh_token'] = token_dico.get('refresh_token')
        config_parameters.set_param('sharepoint_refresh_token', token_dico.get('refresh_token'))

    @api.multi
    def button_get_auth_code_sharepoint(self):
        """
        Request an authorization code for ndp@sirailgroup.com to microsoft to be able to do modifications on Sharepoint.
        """

        full_redirect_uri = self.env['ir.config_parameter'].get_param('web.base.url') + u"/sirail_sharepoint"
        dbname = self.env.cr.dbname

        params = {
            'client_id': u"67e8fd34-23ba-4806-8e15-35a6568b4da3",
            'response_type': u"code",
            'redirect_uri': full_redirect_uri,
            'response_mode': u"query",
            'scope': u"openid offline_access https://sirail.sharepoint.com/user.read",
            'state': json.dumps({'d': dbname}),
        }
        encoded_params = urllib.urlencode(params)
        url = self.auth_code_url_sharepoint + u"/common/oauth2/v2.0/authorize?" + encoded_params

        return {
            'type': "ir.actions.act_url",
            'url': url,
            'target': "new"}

    @api.model
    def get_refresh_token(self, authorization_code):
        """
        Allow to get the refresh_token using the authorization code.
        """

        config_parameters = self.env['ir.config_parameter']
        redirect_uri = self.env['ir.config_parameter'].get_param('web.base.url') + u"/sirail_sharepoint"

        headers = {
            'Content-Type': u"application/x-www-form-urlencoded",
        }

        data = {
            'client_id': u"67e8fd34-23ba-4806-8e15-35a6568b4da3",
            'scope': u"openid offline_access https://sirail.sharepoint.com/user.read",
            'code': authorization_code,
            'redirect_uri': redirect_uri,
            'grant_type': u"authorization_code",
            'client_secret': u"Q:>QIg|I>+cE#&Vv:&=(5+ld{q[_LF%@o!=};{c1#3)",
        }

        request_token = requests.post(u"https://login.microsoftonline.com/common/oauth2/v2.0/token",
                                      headers=headers, data=data)
        token_dico = request_token.json()

        vals = {}
        vals['sharepoint_refresh_token'] = token_dico.get('refresh_token')
        config_parameters.set_param('sharepoint_refresh_token', token_dico.get('refresh_token'))

    def get_token(self):
        """
        Allow to get a new token using the refresh_token when the access_token is not valid anymore (3600s).
        """

        sharepoint_refresh_token = self.env['ir.config_parameter'].get_param('sharepoint_refresh_token')
        redirect_uri = self.env['ir.config_parameter'].get_param('web.base.url') + u"/sirail_sharepoint"

        headers = {
            'Content-Type': u"application/x-www-form-urlencoded",
        }

        data = {
            'client_id': u"67e8fd34-23ba-4806-8e15-35a6568b4da3",
            'scope': u"openid offline_access https://sirail.sharepoint.com/user.read",
            'refresh_token': sharepoint_refresh_token,
            'redirect_uri': redirect_uri,
            'grant_type': u"refresh_token",
            'client_secret': u"Q:>QIg|I>+cE#&Vv:&=(5+ld{q[_LF%@o!=};{c1#3)",
        }

        request_token = requests.post(u"https://login.microsoftonline.com/common/oauth2/v2.0/token",
                                      headers=headers, data=data)
        token_dico = request_token.json()
        sharepoint_token = token_dico.get('access_token')

        return sharepoint_token

    @api.model
    def cron_get_new_refresh_token(self, jobify=True):
        """
        Cron to refresh the refresh_token every month.
        """

        if jobify:
            job_get_refresh_token.delay(ConnectorSession.from_env(self.env), 'knowledge.config.settings',
                                        dict(self.env.context))

        else:
            job_get_refresh_token(ConnectorSession.from_env(self.env), 'knowledge.config.settings',
                                  dict(self.env.context))
