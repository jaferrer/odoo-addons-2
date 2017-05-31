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

import logging
import socket
import requests
import json
import base64
import urllib
from datetime import datetime

from openerp.addons.connector.exception import (NetworkRetryableError,
                                                RetryableJobError)
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter

_logger = logging.getLogger(__name__)

recorder = {}


def call_to_key(method, arguments):
    """ Used to 'freeze' the method and arguments of a call to magentoextendCommerce
    so they can be hashable; they will be stored in a dict.

    Used in both the recorder and the tests.
    """

    def freeze(arg):
        if isinstance(arg, dict):
            items = dict((key, freeze(value)) for key, value
                         in arg.iteritems())
            return frozenset(items.iteritems())
        elif isinstance(arg, list):
            return tuple([freeze(item) for item in arg])
        else:
            return arg

    new_args = []
    for arg in arguments:
        new_args.append(freeze(arg))
    return (method, tuple(new_args))


def record(method, arguments, result):
    """ Utility function which can be used to record test data
    during synchronisations. Call it from magentoextendCRUDAdapter._call

    Then ``output_recorder`` can be used to write the data recorded
    to a file.
    """
    recorder[call_to_key(method, arguments)] = result


def output_recorder(filename):
    import pprint
    with open(filename, 'w') as f:
        pprint.pprint(recorder, f)
    _logger.debug('recorder written to file %s', filename)


class magentoextendLocation(object):
    def __init__(self, param):
        self.param = param


class magentoextendCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for magentoextend """

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(magentoextendCRUDAdapter, self).__init__(connector_env)
        backend = self.backend_record
        param = self.env[backend.connector_id.line_id.type_id.model_name].search(
            [('line_id', '=', backend.connector_id.line_id.id)])
        magentoextend = magentoextendLocation(
            param
        )
        self.magentoextend = magentoextend
        self.token = False

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

    def _create_token(self):
        proxy = self.magentoextend.param.url.replace("http://", "")

        proxy = "http://" + proxy
        parameters = {
            'username': self.magentoextend.param.api_user,
            'password': self.magentoextend.param.api_pwd
        }
        data = json.dumps(parameters)
        head = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.magentoextend.param.use_http:
            head['Authorization'] = 'Basic ' + base64.encodestring(
                self.magentoextend.param.http_user + ":" + self.magentoextend.param.http_pwd)

        s = requests.Session()
        url = proxy + "/integration/admin/token"
        ret = s.post(url, data=data, headers=head)

        self.token = ret.text.replace('"', '')

    def _call(self, method, arguments, meth="GET"):
        try:
            _logger.debug("Start calling magentoextend api %s", method)

            proxy = self.magentoextend.param.url.replace("http://","")

            proxy = "http://" + proxy
            head = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            if self.magentoextend.param.use_http:
                head['Authorization'] = 'Basic ' + base64.encodestring(self.magentoextend.param.http_user + ":" + self.magentoextend.param.http_pwd)

            s = requests.Session()
            if not self.token:
                self._create_token()

            start = datetime.now()
            head["Authorization"] = "Bearer %s" % (self.token)
            try:
                print method
                if meth == "GET":
                    result = s.get(proxy+'/'+method, params=arguments, headers=head)
                    test = result.json()
                    if not isinstance(test, list) and test.get("message"):
                        _logger.error("api call failed %s %s %", method, arguments, test.get("message"))
                    print result.url
                else:
                    result = s.post(proxy + '/' + method, data=json.dumps(arguments), headers=head)
            except:
                _logger.error("api.call(%s, %s) failed", method, arguments)
                raise
            else:
                _logger.debug("api.call(%s, %s) returned %s in %s seconds",
                              method, arguments, result,
                              (datetime.now() - start).seconds)
            return result.json()
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)
        except requests.ProtocolError as err:
            if err.errcode in [502,  # Bad gateway
                               503,  # Service unavailable
                               504]:  # Gateway timeout
                raise RetryableJobError(
                    'A protocol error caused the failure of the job:\n'
                    'URL: %s\n'
                    'HTTP/HTTPS headers: %s\n'
                    'Error code: %d\n'
                    'Error message: %s\n' %
                    (err.url, err.headers, err.errcode, err.errmsg))
            else:
                raise


class GenericAdapter(magentoextendCRUDAdapter):
    _model_name = None
    _magentoextend_model = None

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return self._call('%s' % self._magentoextend_model,
                          filters)

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        arguments = {}
        items = self._call('%s/%s' % (self._magentoextend_model, id),
                           arguments)
        return items

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        return self._call('%s.list' % self._magentoextend_model, [filters])

    def create(self, data):
        """ Create a record on the external system """
        return self._call('%s' % self._magentoextend_model, [data])

    def write(self, id, data):
        """ Update records on the external system """
        return self._call('%s' % self._magentoextend_model,
                          [int(id), data])

    def delete(self, id):
        """ Delete a record on the external system """
        return self._call('%s' % self._magentoextend_model, [int(id)])
