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

from openerp import models, fields


class ConnectorHome(models.Model):
    _name = 'backend.home'

    name = fields.Char(string=u'Name', required=True)
    comment = fields.Text(string=u'Comment')
    connector_ids = fields.One2many('backend.connector.info.line', 'home_id', string=u"Connectors")
    type_ids = fields.One2many('backend.type.line', 'home_id', string=u"Connector Type")


class ConnectorHomeLine(models.Model):
    _name = 'backend.connector.info.line'

    home_id = fields.Many2one('backend.home', string=u"Backend home")
    connector_id = fields.Many2one('backend.connector.info', string=u"Backend Connector")
    image = fields.Binary("Icon", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", required=True, related="connector_id.image")


class ConnectorInfo(models.Model):
    _name = 'backend.connector.info'

    name = fields.Char(string=u'Name', required=True)
    comment = fields.Text(string=u'Comment')
    model_name = fields.Char(string=u'Model Name')
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.")


class ConnectorTypeBackend(models.Model):
    _name = 'backend.type.line'

    home_id = fields.Many2one('backend.home', string=u"Backend home")
    name = fields.Char(string=u'Name', required=True)
    type_id = fields.Char(string=u'Model Name', required=True)
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", related="type_id.image")


class ConnectorTypeBackend(models.Model):
    _name = 'backend.type'

    name = fields.Char(string=u'Name', required=True)
    comment = fields.Text(string=u'Comment')
    model_name = fields.Char(string=u'Model Name')
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.")
