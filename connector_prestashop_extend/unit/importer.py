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
import openerp

from contextlib import closing, contextmanager

from openerp.addons.connector.unit.synchronizer import Importer
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.connector import ConnectorUnit, Binder
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import (
    RetryableJobError,
    FailedJobError,
)

from openerp import _
from ..connector import get_environment

_logger = logging.getLogger(__name__)

RETRY_ON_ADVISORY_LOCK = 1  # seconds
RETRY_WHEN_CONCURRENT_DETECTED = 1 # seconds


class prestashopextendImporter(Importer):
    """ Base importer for magentoextendCommerce """

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(prestashopextendImporter, self).__init__(connector_env)
        self.prestashopextend_id = None
        self.prestashopextend_record = None

    def _get_prestashopextend_data(self):
        return self.backend_adapter.read(self.prestashopextend_id)

    def _has_to_skip(self):
        """ Return True if the import can be skipped """
        return False

    def _before_import(self):
        """ Hook called before the import, when we have the magentoextendCommerce
        data"""

    def _import_dependency(self, prestashopextend_id, binding_model,
                           importer_class=None, always=False, **kwargs):
        """ Import a dependency.

        The importer class is a class or subclass of
        :class:`magentoextendImporter`. A specific class can be defined.

        :param magentoextend_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_cls: :class:`openerp.addons.connector.\
                                     connector.ConnectorUnit`
                             class or parent class to use for the export.
                             By default: magentoextendImporter
        :type importer_cls: :class:`openerp.addons.connector.\
                                    connector.MetaConnectorUnit`
        :param always: if True, the record is updated even if it already
                       exists, note that it is still skipped if it has
                       not been modified on magentoextendCommerce since the last
                       update. When False, it will import it only when
                       it does not yet exist.
        :type always: boolean
        """
        if not prestashopextend_id:
            return
        if importer_class is None:
            importer_class = prestashopextendImporter
        binder = self.binder_for(binding_model)
        if always or binder.to_openerp(prestashopextend_id) is None:
            importer = self.unit_for(importer_class, model=binding_model)
            importer.run(prestashopextend_id,**kwargs)

    def _import_dependencies(self):
        """ Import the dependencies for the record

        Import of dependencies can be done manually or by calling
        :meth:`_import_dependency` for each dependency.
        """
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`

        """
        return self.mapper.map_record(self.prestashopextend_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _get_binding(self):
        return self.binder.to_openerp(self.prestashopextend_id, browse=True)

    def _context(self, **kwargs):
        return dict(self.session.context, connector_no_export=True, **kwargs)

    def _create_context(self):
        return {'connector_no_export': True}

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding = self.model.with_context(
            **self._create_context()
        ).create(data)
        _logger.debug('%d created from prestashopextend %s', binding, self.prestashopextend_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from magentoextend %s', binding, self.prestashopextend_id)
        return

    def _before_import(self):
        """ Hook called before the import, when we have the PrestaShop
        data"""
        return

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    @contextmanager
    def do_in_new_connector_env(self, model_name=None):
        """ Context manager that yields a new connector environment
        Using a new Odoo Environment thus a new PG transaction.
        This can be used to make a preemptive check in a new transaction,
        for instance to see if another transaction already made the work.
        """
        with openerp.api.Environment.manage():
            registry = openerp.modules.registry.RegistryManager.get(
                self.env.cr.dbname
            )
            with closing(registry.cursor()) as cr:
                try:
                    new_env = openerp.api.Environment(cr, self.env.uid,
                                                      self.env.context)
                    new_connector_session = ConnectorSession.from_env(new_env)
                    connector_env = self.connector_env.create_environment(
                        self.backend_record.with_env(new_env),
                        new_connector_session,
                        model_name or self.model._name,
                        connector_env=self.connector_env
                    )
                    yield connector_env
                except:
                    cr.rollback()
                    raise
                else:
                    # Despite what pylint says, this a perfectly valid
                    # commit (in a new cursor). Disable the warning.
                    cr.commit()  # pylint: disable=invalid-commit

    def run(self, prestashopextend_id, **kwargs):
        """ Run the synchronization

        :param magentoextend_id: identifier of the record on magentoextendCommerce
        """
        self.prestashopextend_id = prestashopextend_id
        lock_name = 'import({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.prestashopextend_id,
        )
        # Keep a lock on this import until the transaction is committed
        self.advisory_lock_or_retry(lock_name,
                                    retry_seconds=RETRY_ON_ADVISORY_LOCK)
        self.prestashopextend_record = self._get_prestashopextend_data()

        binding = self._get_binding()
        if not binding:
            with self.do_in_new_connector_env() as new_connector_env:
                binder = new_connector_env.get_connector_unit(Binder)
                if binder.to_openerp(self.prestashopextend_id):
                    raise RetryableJobError(
                        'Concurrent error. The job will be retried later',
                        seconds=RETRY_WHEN_CONCURRENT_DETECTED,
                        ignore_retry=True
                    )
        skip = self._has_to_skip()
        if skip:
            return skip

        # import the missing linked resources
        self._import_dependencies()

        self._import(binding, **kwargs)

    def _import(self, binding, **kwargs):
        """ Import the external record.
        Can be inherited to modify for instance the session
        (change current user, values in context, ...)
        """

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
        else:
            record = self._create_data(map_record)

        # special check on data before import
        self._validate_data(record)

        if binding:
            self._update(binding, record)
        else:
            binding = self._create(record)

        self.binder.bind(self.prestashopextend_id, binding)

        self._after_import(binding)


class BatchImporter(Importer):
    """ The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    page_size = 1000

    def run(self, filters=None, **kwargs):
        """ Run the synchronization """
        if filters is None:
            filters = {}
        if 'limit' in filters:
            self._run_page(filters, **kwargs)
            return
        page_number = 0
        filters['limit'] = '%d,%d' % (
            page_number * self.page_size, self.page_size)
        record_ids = self._run_page(filters, **kwargs)
        while len(record_ids) == self.page_size:
            page_number += 1
            filters['limit'] = '%d,%d' % (
                page_number * self.page_size, self.page_size)
            record_ids = self._run_page(filters, **kwargs)

    def _run_page(self, filters, **kwargs):
        record_ids = self.backend_adapter.search(filters)
        self._import_record(record_ids, **kwargs)
        return record_ids

    def _import_record(self, record):
        """ Import a record directly or delay the import of the record """
        raise NotImplementedError


class AddCheckpoint(ConnectorUnit):
    """ Add a connector.checkpoint on the underlying model
    (not the prestashop.* but the _inherits'ed model) """

    _model_name = []

    def run(self, binding_id):
        record = self.model.browse(binding_id)
        self.backend_record.add_checkpoint(
            session=self.session,
            model=record._model._name,
            record_id=record.id,
        )


class DirectBatchImporter(BatchImporter):
    """ Import the records directly, without delaying the jobs. """
    _model_name = None

    def _import_record(self, record_ids):
        """ Import the record directly """
        import_record(self.session,
                      self.model._name,
                      self.backend_record.id,
                      record_ids)


class TranslatableRecordImporter(prestashopextendImporter):
    """ Import one translatable record """
    _model_name = []

    _translatable_fields = {}
    # TODO set default language on the backend
    _default_language = 'en_US'

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.ConnectorEnvironment`
        """
        super(TranslatableRecordImporter, self).__init__(environment)
        self.main_lang_data = None
        self.main_lang = None
        self.other_langs_data = None

    def _get_odoo_language(self, prestashop_id):
        language_binder = self.binder_for('prestashopextend.res.lang')
        erp_language = language_binder.to_odoo(prestashop_id)
        return erp_language

    def find_each_language(self, record):
        languages = {}
        for field in self._translatable_fields[self.connector_env.model_name]:
            # TODO FIXME in prestapyt
            if not isinstance(record[field]['language'], list):
                record[field]['language'] = [record[field]['language']]
            for language in record[field]['language']:
                if not language or language['attrs']['id'] in languages:
                    continue
                #erp_lang = self._get_odoo_language(language['attrs']['id'])
                erp_lang = False
                if erp_lang:
                    languages[language['attrs']['id']] = erp_lang.code
        return {"1": "fr_FR"}

    def _split_per_language(self, record, fields=None):
        """Split record values by language.
        @param record: a record from PS
        @param fields: fields whitelist
        @return a dictionary with the following structure:
            'en_US': {
                'field1': value_en,
                'field2': value_en,
            },
            'it_IT': {
                'field1': value_it,
                'field2': value_it,
            }
        """
        split_record = {}
        languages = self.find_each_language(record)
        if not languages:
            raise FailedJobError(
                _('No language mapping defined. '
                  'Run "Synchronize base data".')
            )
        model_name = self.connector_env.model_name
        for language_id, language_code in languages.iteritems():
            split_record[language_code] = record.copy()
        _fields = self._translatable_fields[model_name]
        if fields:
            _fields = [x for x in _fields if x in fields]
        for field in _fields:
            for language in record[field]['language']:
                current_id = language['attrs']['id']
                code = languages.get(current_id)
                if code:
                    split_record[code][field] = language['value']
        return split_record

    def _create_context(self):
        context = super(TranslatableRecordImporter, self)._create_context()
        if self.main_lang:
            context['lang'] = self.main_lang
        return context

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`
        """
        return self.mapper.map_record(self.main_lang_data)

    def _import(self, binding, **kwargs):
        """ Import the external record.
        Can be inherited to modify for instance the session
        (change current user, values in context, ...)
        """
        # split prestashop data for every lang
        split_record = self._split_per_language(self.prestashopextend_record)
        if self._default_language in split_record:
            self.main_lang_data = split_record[self._default_language]
            self.main_lang = self._default_language
            del split_record[self._default_language]
        else:
            self.main_lang, self.main_lang_data = split_record.popitem()

        self.other_langs_data = split_record

        super(TranslatableRecordImporter, self)._import(binding)

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        for lang_code, lang_record in self.other_langs_data.iteritems():
            map_record = self.mapper.map_record(lang_record)
            binding.with_context(
                lang=lang_code,
                connector_no_export=True,
            ).write(map_record.values())


class DelayedBatchImporter(BatchImporter):
    """ Delay import of the records """
    _model_name = None

    def _import_record(self, record_ids, **kwargs):
        """ Delay the import of the records"""
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_ids,
                            **kwargs)


@job(default_channel='root.prestashopextend')
def import_batch(session, model_name, backend_id, filters=None, **kwargs):
    """ Prepare a batch import of records from PrestaShop """
    backend = session.env['prestashopextend.backend'].browse(backend_id)
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(BatchImporter)
    importer.run(filters=filters, **kwargs)


@job(default_channel='root.prestashopextend')
def import_record(
        session, model_name, backend_id, prestashop_ids, **kwargs):
    """ Import a record from PrestaShop """
    backend = session.env['prestashopextend.backend'].browse(backend_id)
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(prestashopextendImporter)
    log = ""
    for id in prestashop_ids:
        log = log + '\n' + str(id) + '\n' + '----------' + '\n'
        resp = str(importer.run(id, **kwargs))
        log = log + resp

    return log
