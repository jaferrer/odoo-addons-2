# -*- coding: utf-8 -*-
#
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

from openerp import exceptions, _

import logging
import base64
import socket
import xmlrpclib
from datetime import datetime

from openerp.addons.connector.exception import (NetworkRetryableError,
                                                RetryableJobError)
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from contextlib import contextmanager
from requests.exceptions import HTTPError, RequestException, ConnectionError
_logger = logging.getLogger(__name__)
try:
    from prestapyt import PrestaShopWebServiceDict, PrestaShopWebServiceError
except:
    _logger.debug('Cannot import from `prestapyt`')


recorder = {}


@contextmanager
def api_handle_errors(message=''):
    """ Handle error when calling the API
    It is meant to be used when a model does a direct
    call to a job using the API (not using job.delay()).
    Avoid to have unhandled errors raising on front of the user,
    instead, they are presented as :class:`openerp.exceptions.UserError`.
    """
    if message:
        message = message + u'\n\n'
    try:
        yield
    except NetworkRetryableError as err:
        raise exceptions.UserError(
            _(u'{}Network Error:\n\n{}').format(message, err)
        )
    except (HTTPError, RequestException, ConnectionError) as err:
        raise exceptions.UserError(
            _(u'{}API / Network Error:\n\n{}').format(message, err)
        )
    except PrestaShopWebServiceError as err:
        raise exceptions.UserError(
            _(u'{}Authentication Error:\n\n{}').format(message, err)
        )
    except PrestaShopWebServiceError as err:
        raise exceptions.UserError(
            _(u'{}Error during synchronization with '
                'PrestaShop:\n\n{}').format(message, unicode(err))
        )


class PrestaShopWebServiceImage(PrestaShopWebServiceDict):

    def get_image(self, resource, resource_id=None, image_id=None,
                  options=None):
        full_url = self._api_url + 'images/' + resource
        if resource_id is not None:
            full_url += "/%s" % (resource_id,)
            if image_id is not None:
                full_url += "/%s" % (image_id)
        if options is not None:
            self._validate_query_options(options)
            full_url += "?%s" % (self._options_to_querystring(options),)
        response = self._execute(full_url, 'GET')
        if response.content:
            image_content = base64.b64encode(response.content)
        else:
            image_content = ''

        record = {
            'type': response.headers['content-type'],
            'content': image_content,
            'id_' + resource[:-1]: resource_id,
            'id_image': image_id,
        }
        record['full_public_url'] = self.get_image_public_url(record)
        return record

    def get_image_public_url(self, record):
        url = self._api_url.replace('/api', '')
        url += '/img/p/' + '/'.join(list(record['id_image']))
        extension = ''
        if record['type'] == 'image/jpeg':
            extension = '.jpg'
        url += '/' + record['id_image'] + extension
        return url



class prestashopextendLocation(object):
    def __init__(self, param):
        self.param = param
        self.location = param.location
        location = param.location
        self.webservice_key = param.webservice_key
        if not location.endswith('/api'):
            location = location + '/api'
        if not location.startswith('http'):
            location = 'http://' + location
        self.api_url = location


class prestashopextendCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for prestashopextendCRUDAdapter """

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(prestashopextendCRUDAdapter, self).__init__(connector_env)
        backend = self.backend_record
        param = self.env[backend.connector_id.line_id.type_id.model_name].search(
            [('line_id', '=', backend.connector_id.line_id.id)])
        prestashopextend = prestashopextendLocation(
            param
        )
        self.prestashopextend = prestashopextend

        self.client = PrestaShopWebServiceDict(
            self.prestashopextend.api_url,
            self.prestashopextend.webservice_key,
        )

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, attributes=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError

    def head(self):
        """ HEAD """
        raise NotImplementedError


class GenericAdapter(prestashopextendCRUDAdapter):
    _model_name = None
    _prestashopextend_model = None
    _export_node_name = ''
    _export_node_name_res = ''

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids
        :rtype: list
        """
        _logger.debug(
            'method search, model %s, filters %s',
            self._prestashopextend_model, unicode(filters))
        return self.client.search(self._prestashopextend_model, filters)

    def read(self, id, attributes=None):
        """ Returns the information of a record
        :rtype: dict
        """
        _logger.debug(
            'method read, model %s id %s, attributes %s',
            self._prestashopextend_model, str(id), unicode(attributes))
        res = self.client.get(self._prestashopextend_model, id, options=attributes)
        first_key = res.keys()[0]
        return res[first_key]

    def create(self, attributes=None):
        """ Create a record on the external system """
        _logger.debug(
            'method create, model %s, attributes %s',
            self._prestashopextend_model, unicode(attributes))
        return self.client.add(self._prestashopextend_model, {
            self._export_node_name: attributes
        })

    def write(self, id, attributes=None):
        """ Update records on the external system """
        attributes['id'] = id
        _logger.debug(
            'method write, model %s, attributes %s',
            self._prestashopextend_model,
            unicode(attributes)
        )
        return self.client.edit(
            self._prestashopextend_model, {self._export_node_name: attributes})

    def delete(self, resource, ids):
        _logger.debug('method delete, model %s, ids %s',
                      resource, unicode(ids))
        # Delete a record(s) on the external system
        return self.client.delete(resource, ids)

    def head(self, id=None):
        """ HEAD """
        return self.client.head(self._prestashopextend_model, resource_id=id)
