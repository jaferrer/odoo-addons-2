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
from datetime import datetime
from openerp.addons.connector.unit.synchronizer import Importer
from openerp import _, exceptions

_logger = logging.getLogger(__name__)


class BusextendImporter(Importer):

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(BusextendImporter, self).__init__(connector_env)
        self.busextend_id = None
        self.busextend_record = None
        self.busextend_record_translation = None
        self.bus_model = None

    def _before_import(self):
        """ Hook called before the import, when we have the magentoextendCommerce
        data"""

    def _is_uptodate(self, binding):
        return False

    def _import_dependency(self, busextend_record, bus_model, dependency,
                           importer_class=None, always=False, ):
        if not busextend_record:
            return
        if importer_class is None:
            importer_class = BusextendImporter
        importer = self.unit_for(importer_class, model="bus.receive.transfer")
        depend = importer.run(busextend_record, bus_model, self.dependency)
        return depend

    def _import_dependencies(self):

        record = self.busextend_record

        for obj in record.keys():
            if isinstance(record.get(obj), dict) and obj not in ["_dependency", "_bus_model"]:
                recs = self.get_records_for_dependency(record, obj)
                for rec in recs:
                    depend = self._import_dependency(rec, record.get(obj).get("model"), self.dependency)
                    if depend:
                        return True
        return False

    def get_records_for_dependency(self, record, obj):
        rec = []
        if "ids" in record.get(obj):
            for id in record.get(obj).get("ids"):
                if record.get(obj).get("model") in self.dependency and str(id) in self.dependency.get(
                        record.get(obj).get("model")):
                    rec.append(self.dependency.get(record.get(obj).get("model")).get(str(id)))
        elif record.get(obj).get("model") in self.dependency and str(record.get(obj).get("id")) in self.dependency.get(
                record.get(obj).get("model")):
            rec.append(self.dependency.get(record.get(obj).get("model")).get(str(record.get(obj).get("id"))))
        return rec

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`

        """
        map_record = self.mapper.map_record(self.busextend_record)
        return map_record

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode

        model = str(model).split('()')[0]       """
        return

    def _get_binding(self, busxentend_id, model):
        return self.binder.to_openerp(busxentend_id, model, browse=True)

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data, migration):
        """ Create the OpenERP record """
        # special check on data before import
        self._validate_data(data)
        model = self.model.with_context(connector_no_export=True)._name
        binding = self.env[model].with_context(migration=migration).create(data)
        _logger.debug('%d created from busextend %s %s', binding, self.busextend_id, self.bus_model)
        return binding

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding, data, migration):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True, migration=migration).write(data)
        _logger.debug('%d updated from busextend %s %s', binding, self.busextend_id, self.bus_model)
        return

    def _update_translation(self, binding):
        if self.busextend_record_translation:
            for field in self.busextend_record_translation:
                for lang in self.busextend_record_translation.get(field):
                    trad = self.busextend_record_translation.get(field).get(lang)
                    ir_translation_name = "%s,%s" % (binding.model, field)
                    ir_translation = self.env['ir.translation'].search([('name', '=', ir_translation_name),
                                                                        ('type', '=', 'model'), ('lang', '=', lang),
                                                                        ('res_id', '=', binding.local_id)])
                    trad.update({'comments': u"Set by BUS %s" % datetime.now()})
                    if ir_translation:
                        ir_translation.write(trad)
                    else:
                        trad.update({
                            'name': ir_translation_name,
                            'lang': lang,
                            'res_id': binding.local_id,
                            'type': 'field'
                        })
                        self.env['ir.translation'].create(trad)
        return True

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def run(self, record, bus_model, dependency_list, force=False):
        """ Run the synchronization """

        self.busextend_id = record.get("external_key")
        translation = record.get('translation', False)
        record.update({'translation': False})
        self.busextend_record = record
        self.busextend_record_translation = translation
        self.bus_model = bus_model
        self.dependency = dependency_list

        self.busextend_record["_bus_model"] = bus_model
        self.busextend_record["_dependency"] = self.dependency

        skip = self._must_skip()
        if skip:
            return skip

        binding = self._get_binding(self.busextend_id, self.bus_model)
        model_map = self.env["bus.object.mapping"].search([("name", "=", self.bus_model),
                                                       ("active", "=", True),
                                                       ("transmit", "=", True)])
        object = True
        link_model = False
        if binding:
            object = self.env[self.bus_model].search([('id', '=', binding.local_id)])
        if not binding and len(self.busextend_record.keys()) < 6 or binding and not object:
            return {
                "model": bus_model,
                "external_key": self.busextend_id
            }
        elif not binding:
            if model_map.key_xml_id and "xml_id" in record:
                module, name = record["xml_id"].split(".")
                ir_model_data = self.env['ir.model.data'].search(
                    [('model', '=', model_map.name), ('module', '=', module), ('name', '=', name)])
                link_model = self.env[self.bus_model].search([("id", "=", ir_model_data.res_id)])
            if not model_map.key_xml_id or not link_model:
                map_field = self.env["bus.object.mapping.field"].search([("migration", '=', True),
                                                                     ("object_id", "=", model_map.id)])
                domain = []
                if map_field:
                    for field in map_field:
                        domain = self.get_domain(field, domain)
                    if domain:
                        link_model = self.env[self.bus_model].search(domain)

            if link_model and len(link_model) == 1:
                if binding:
                    binding.local_id = link_model[0].id
                else:
                    binding = self.env["bus.receive.transfer"].create({
                        "model": self.bus_model,
                        "local_id": link_model[0].id,
                        "external_key": self.busextend_id
                    })

        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')

        dependencies = self._import_dependencies()
        if dependencies:
            return False
        map_record = self._map_data()
        if binding:
            datas = self._update_data(map_record)
            self._update(binding, datas, model_map.migration)
            self._update_translation(binding)
        else:
            datas = self._create_data(map_record)
            binding = self._create(datas, model_map.migration)
            self._update_translation(binding)
            record["local_id"] = binding.local_id
            return record

    def get_domain(self, field, domain):
        domain_item = False
        if self.busextend_record.get(str(field.map_name)):
            if isinstance(self.busextend_record.get(field.map_name), dict):
                external_id = str(self.busextend_record.get(field.map_name).get('id'))
                external_key = self.dependency.get(field.relation).get(external_id).get('external_key')
                external_binding = self._get_binding(external_key, field.relation)
                domain_item = (field.name, "=", external_binding.local_id)
            else:
                domain_item = (field.name, "=", self.busextend_record.get(field.map_name))
        if domain_item:
            domain.append(domain_item)
        return domain

    def run_deletion_return(self, record, bus_model, dependency_list, force=False):
        self.busextend_id = record.get("id", 0)
        self.busextend_record = record
        self.bus_model = bus_model
        self.busextend_model = record.get("model", False)
        self.busextend_local_id = record.get("local_id", 0)
        self.dependency = dependency_list
        binding = self.env[self.bus_model].search([('id', "=", self.busextend_id)])
        if binding and binding.to_deactivate and binding.local_id == self.busextend_local_id:
            object = self.env[self.busextend_model].search([("id", "=", self.busextend_local_id)])
            if object and object.id:
                raise exceptions.except_orm(u"Error",
                                            u"Unable to delete binding, some object already exist: %s") % record
            binding.unlink()
        return True

    def run_deletion(self, record, bus_model, dependency_list, force=False):
        self.busextend_id = record.get("external_key")
        self.busextend_record = record
        self.bus_model = bus_model
        self.dependency = dependency_list
        self.busextend_record["_bus_model"] = bus_model
        self.busextend_record["_dependency"] = self.dependency
        unlink = "False"
        model_to_delete = record.get("model", "")
        id_to_delete = record.get("local_id", "")
        external_key_to_delete = self.dependency.get(model_to_delete, "").get(id_to_delete, "").get("external_key")
        if external_key_to_delete and record.get("to_deactivate", False):
            binding_to_delete = self.env["bus.receive.transfer"].search(
                [("model", "=", model_to_delete), ("external_key", "=", external_key_to_delete)])
            if binding_to_delete:
                record_to_delete = self.env[model_to_delete].browse(binding_to_delete.local_id)
                if record_to_delete:
                    record_to_delete.write({"active": False})
                    unlink = "Ok"
                binding_to_delete.write({"to_deactivate": False})
            else:
                unlink = "null"
        return unlink


BusextendImportSynchronizer = BusextendImporter
