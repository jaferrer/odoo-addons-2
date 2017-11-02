# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class ConnectorHome(models.Model):
    _name = 'backend.home'

    name = fields.Char(string=u'Name', required=True)
    comment = fields.Text(string=u'Comment')
    warehouse_id = fields.Many2one('stock.warehouse', string=u"Warehouse")
    connector_pull_ids = fields.One2many('backend.connector.info.line', 'home_id', string=u"Connectors",
                                         domain=[('type', '=', 'PULL')])
    connector_push_ids = fields.One2many('backend.connector.info.line', 'home_id', string=u"Connectors",
                                         domain=[('type', '=', 'PUSH')])
    type_ids = fields.One2many('backend.type.line', 'home_id', string=u"Connector Type")
    partner_id = fields.Many2one('res.partner', string=u"Owner", required=True)


class ConnectorHomeLine(models.Model):
    _name = 'backend.connector.info.line'

    home_id = fields.Many2one('backend.home', string=u"Backend home")
    connector_id = fields.Many2one('backend.connector.info', string=u"Backend Connector", required=True)
    image = fields.Binary("Icon", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", required=True, related="connector_id.image")
    type = fields.Selection([("PULL", "Pull Data"), ("PUSH", "Push Data")], string=u"Type", required=True,
                            related="connector_id.type", store=True)
    line_id = fields.Many2one('backend.type.line', string=u"Connector Type line", required=True)

    cron = fields.Boolean('cron is active', compute="_compute_cron")
    init_conf = fields.Boolean('Init conf', store=True)
    active = fields.Boolean('Actif', store=True, default=True)

    @api.multi
    def _compute_cron(self):
        for rec in self:
            cron = self.env['ir.cron'].search([('connector_id', '=', rec.id)])
            if cron:
                rec.cron = cron.active
            else:
                rec.cron = False

    @api.multi
    def create_backend(self):
        self.ensure_one()
        param = self.env[self.connector_id.model_name].search([('connector_id', '=', self.id)])
        if not param:
            self.env[self.connector_id.model_name].create({
                'connector_id': self.id,
                'name': "%s - %s" % (self.id, self.connector_id.model_name),
                'warehouse_id': 1
            })
            self._create_cron()
        self.write({
            "init_conf": True
        })

    @api.multi
    def run_batch(self):
        self.ensure_one()
        param = self.env[self.connector_id.model_name].search([('connector_id', '=', self.id)])
        getattr(param, self.connector_id.method_name)()

    def _create_cron(self):
        back = self.env[self.connector_id.model_name].search([('connector_id', '=', self.id)])
        item = {
            'connector_id': self.id,
            'name': u"Sync %s for %s" % (self.connector_id.name, self.home_id.partner_id.name),
            'user_id': 1,
            'priority': 100,
            'interval_type': 'hours',
            'interval_number': 1,
            'numbercall': -1,
            'doall': False,
            'model': self.connector_id.model_name,
            'function': u'cron_%s' % (self.connector_id.method_name),
            'args': "(%s)" % repr([back.id]),
            'active': False
        }
        cron = self.env['ir.cron'].create(item)
        return cron

    @api.multi
    def edit_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].search(
            ['&', ('connector_id', '=', self.id), '|', ('active', '=', False), ('active', '=', True)])
        if not cron:
            cron = self._create_cron()
        return {
            'name': 'Cron',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ir.cron',
            'res_id': cron.id,
            'context': False
        }

    @api.multi
    def unlink(self):
        crons = self.env['ir.cron'].search(
            ['&', ('connector_id', 'in', self.ids), '|', ('active', '=', False), ('active', '=', True)])
        if crons:
            crons.unlink()
        self.active = False


class BackendHomeCron(models.Model):
    _inherit = 'ir.cron'

    connector_id = fields.Many2one('backend.connector.info.line', string=u"connector line")


class ConnectorInfo(models.Model):
    _name = 'backend.connector.info'

    name = fields.Char(string=u'Name', required=True)
    comment = fields.Text(string=u'Comment')
    model_name = fields.Char(string=u'Model Name')
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.")
    type = fields.Selection([("PULL", "Pull Data"), ("PUSH", "Push Data")], string=u"Type", required=True)
    backend_type_id = fields.Many2one('backend.type', string=u"Backend type")
    method_name = fields.Char(string=u'Method Name')


class ConnectorTypeBackend(models.Model):
    _name = 'backend.type.line'

    home_id = fields.Many2one('backend.home', string=u"Backend home")
    name = fields.Char(string=u'Name', required=True)
    type_id = fields.Many2one('backend.type', string=u"Connector Type", required=True)
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", related="type_id.image")

    @api.multi
    def open_popup_parameter(self):
        self.ensure_one()
        param = self.env[self.type_id.model_name].search([('line_id', '=', self.id)])
        if not param:
            param = self.env[self.type_id.model_name].create({
                'line_id': self.id
            })
        return {
            'name': 'Parameter',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.type_id.model_name,
            'res_id': param.id,
            'target': 'new',
            'context': False
        }


class ConnectorTypeBackend(models.Model):
    _name = 'backend.type'

    name = fields.Char(string=u'Name', required=True)
    comment = fields.Text(string=u'Comment')
    model_name = fields.Char(string=u'Model Name')
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.")


class ConnectorTypeMagentoParameter(models.Model):
    _name = 'connector.type.magento.parameter'

    url = fields.Char(string=u'api')
    api_user = fields.Char(string=u'Username')
    api_pwd = fields.Char(string=u'Password')

    use_http = fields.Boolean(u"Use HTTP Auth Basic")

    http_user = fields.Char(string=u'Basic Auth. Username')
    http_pwd = fields.Char(string=u'Basic Auth. Password')

    line_id = fields.Many2one('backend.type.line', string=u"Connector Type line", required=True)


class ConnectorTypeOdooParameter(models.Model):
    _name = 'connector.type.odoo.parameter'

    url = fields.Char(string=u'api')
    api_user = fields.Char(string=u'Username')
    api_pwd = fields.Char(string=u'Password')
    db_odoo = fields.Char(string=u'Base de données odoo')

    model_odoo = fields.Char(u"Model Odoo")

    method_odoo = fields.Char(string=u'Method Odoo')

    line_id = fields.Many2one('backend.type.line', string=u"Connector Type line", required=True)


class ConnectorTypeFtpParameter(models.Model):
    _name = 'connector.type.ftp.parameter'

    url = fields.Char(string=u'server')
    user = fields.Char(string=u'Username')
    pwd = fields.Char(string=u'Password')

    protocol = fields.Selection([("FTP", "Ftp"), ("SFTP", "Sftp")], string="Protocol", required=True, default="FTP")
    target_path = fields.Char(string=u'target path')
    archive_path = fields.Char(string=u'archive path')

    line_id = fields.Many2one('backend.type.line', string=u"Connector Type line", required=True)


class ConnectorTypeLocalParameter(models.Model):
    _name = 'connector.type.local.parameter'

    target_path = fields.Char(string=u'target path')
    archive_path = fields.Char(string=u'archive path')

    line_id = fields.Many2one('backend.type.line', string=u"Connector Type line", required=True)

