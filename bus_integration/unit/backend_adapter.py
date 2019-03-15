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

from openerp.addons.connector.unit.backend_adapter import CRUDAdapter

_logger = logging.getLogger(__name__)

RECORDER = {}


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
    RECORDER[call_to_key(method, arguments)] = result


def output_recorder(filename):
    import pprint
    with open(filename, 'w') as file_name:
        pprint.pprint(RECORDER, file_name)
    _logger.debug('RECORDER written to file %s', filename)


class BusextendLocation(object):
    def __init__(self, param):
        self.param = param


class BusextendCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for magentoextend """

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(BusextendCRUDAdapter, self).__init__(connector_env)
        self.backend = self.backend_record
        param = {}
        busextend = BusextendLocation(
            param
        )
        self.busextend = busextend
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


class GenericAdapter(BusextendCRUDAdapter):
    _model_name = None
    _busextend_model = None

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
