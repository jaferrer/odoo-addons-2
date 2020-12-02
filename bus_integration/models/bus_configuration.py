# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import ipaddress
import socket
import logging
from urlparse import urlparse
from requests import get, ConnectionError
from openerp import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class BaseUrlMatchException(exceptions.except_orm):
    def __init__(self, msg):
        super(BaseUrlMatchException, self).__init__(_(u"Error!"), msg)


class BusConfiguration(models.Model):
    _name = 'bus.configuration'
    _inherit = 'bus.send.message'

    name = fields.Char(u"Name")
    sender_id = fields.Many2one('bus.base', u"Sender")
    bus_configuration_export_ids = fields.One2many('bus.configuration.export', 'configuration_id', string=u"Fields")
    reception_treatment = fields.Selection([('simple_reception', u"Simple reception")], u"Message Reception Treatment",
                                           required=True)
    code = fields.Selection([('ODOO_SYNCHRONIZATION', u"Odoo synchronization")], u"Code exchange", required=True)
    connexion_state = fields.Char(u"Connexion status")
    module_disabled_mapping = fields.Char(u"Module disabled mapping", help=u"Module not used for mapping by xml id",
                                          default='__export__')
    keep_messages_for = fields.Integer(string=u"Keep messages for", help=u"In days", default=7)

    @api.model
    def _get_host_name_or_raise(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if not base_url:
            return False
        hostname = urlparse(base_url).hostname
        ip = socket.gethostbyname(hostname)
        # localhost ip base_url matches host device
        if ip == '127.0.0.1':
            return hostname

        # ip might be the public ip
        ipify_url = self.env['ir.config_parameter'].get_param('bus_integration.ipify')
        try:
            public_ip = get(ipify_url).text
        except ConnectionError as ex:
            # fall back behaviour if ipify.org is not available don't block
            _logger.error(repr(ex))
            return hostname

        if ip == public_ip:
            return hostname

        # if ipify.org returns an error => throws a user friendly error
        try:
            ipaddress.ip_address(public_ip)
        except ipaddress.AddressValueError as ex:
            _logger.error(repr(ex))
            raise BaseUrlMatchException('Public ip of %s has not been retreived by %s, '
                                        'please try again later' % (hostname, ipify_url))

        error_message = 'hostname %s resolved as %s does neither match local nor public IP (127.0.0.1 and %s)'
        raise BaseUrlMatchException(error_message % (hostname, ip, public_ip))

    # static var
    _singleton_host_name = False

    @api.multi
    def _get_cached_host_name(self):
        """
        singleton makes _singleton_host_name computed a single time to speed up treatments
        """
        if not BusConfiguration._singleton_host_name:
            BusConfiguration._singleton_host_name = self._get_host_name_or_raise()
        return BusConfiguration._singleton_host_name

    @api.model
    def _is_not_allowed_error_message(self, server, login, hostname):
        """
        see if this odoo instance is known by the bus. return an error if unknown.
        :return: error message
        """
        res = self.send_search_read(server, login,
                                    model='bus.subscriber',
                                    domain=[('url', 'ilike', hostname), ('database', 'ilike', self.env.cr.dbname)],
                                    fields=['url', 'database'])
        if res:  # no error to return..
            return False
        return "Connection refused ! The host \"%s\" with db \"%s\" are not known by the distant bus, " \
               "please check the bus configuration" % (hostname, self.env.cr.dbname)

    @api.multi
    def try_connexion(self, raise_error=False):
        server, result, login = super(BusConfiguration, self).try_connexion(raise_error)

        try:
            hostname = self._get_cached_host_name()
        except BaseUrlMatchException as e:
            if raise_error:
                raise BaseUrlMatchException(e.value)
            else:
                return server, e.message, 0

        error_message = self._is_not_allowed_error_message(server, login, hostname)
        if error_message:
            # web.base.url might be wrongly. we need to recompute cached host name in case the config.parameter change
            BusConfiguration._singleton_host_name = False
            if raise_error:
                raise exceptions.except_orm(_(u"Error!"), error_message)
            return server, error_message, 0
        # all ok
        return server, result, login
