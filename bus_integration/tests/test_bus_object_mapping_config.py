# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import modules
from openerp.tests import common


class TestBusObjectMappingConfig(common.TransactionCase):
    """
    Verifie la présence d'une contrainte d'unicité par modèle ayant une clé de migration composée de champs
    Verifie également que ces champs soient required = column not null
    Ce test doit s'appliquer a la config contenue dans les fichiers data des modules dépendants de bus_integration :
        * sirail_master_get_feed
        * sirail_master_sync
        * sirail_master_feeder
        * sirail_subscriber
    """
    _query_select_constraint = ""
    _query_select_required_fields = ""

    @staticmethod
    def get_sql(file_name):
        sql_file_path = '%s/tests/sql/%s' % (modules.get_module_path('bus_integration'), file_name)
        with open(sql_file_path) as sql_file:
            return sql_file.read()

    def setUp(self):
        # load sql file
        self._query_select_constraint = self.get_sql("select_constraints.sql")
        self._query_select_required_fields = self.get_sql("select_required_fields.sql")
        super(TestBusObjectMappingConfig, self).setUp()

    # region code formatting
    @staticmethod
    def _get_not_null_constraint_sql_code(model_name, required_field):
        model_str = model_name.replace('.', '_')
        field_str = required_field.encode('ascii', 'ignore')
        sql_mask = \
            "ALTER TABLE {0} ALTER COLUMN {1} SET NOT NULL;\n" \
            "ALTER TABLE {0} ALTER COLUMN {1} DROP NOT NULL;"
        return sql_mask.format(model_str, field_str)

    @staticmethod
    def _get_uniq_constraint_sql_code(model_name, required_fields):
        model_str = model_name.replace('.', '_')
        fields_str = ", ".join(f.encode('ascii', 'ignore') for f in required_fields)
        sql_mask = \
            "ALTER TABLE public.{0} ADD CONSTRAINT {0}_bus_mapping_uniq UNIQUE ({1});\n" \
            "ALTER TABLE public.{0} DROP CONSTRAINT {0}_bus_mapping_uniq;\n"
        return sql_mask.format(model_str, fields_str)

    @staticmethod
    def _get_uniq_constraint_python_code(required_fields):
        """
        :param required_fields: champs requis par la contrainte
        :return: la contrainte a insérer en python
        """
        fields_str = ", ".join(f.encode('ascii', 'ignore') for f in required_fields)
        python_mask = "_sql_constraints = [('uq_constraint_bus_mapping', 'UNIQUE({0})', " \
                      "_(u'bus synchronisation requires unique values for : %s') % '{0}')]"
        return python_mask.format(fields_str)
    # endregion

    def _get_nullable_fields(self, model_name, constraint_fields):
        """ :return les champs :constraint_fields n'ayant pas de required=True dans leurs définition python"""
        db_model = model_name.replace('.', '_')
        self.env.cr.execute(self._query_select_required_fields, [db_model])
        required_fields = [result_line['column_name'] for result_line in self.env.cr.dictfetchall()]
        return [constraint_field for constraint_field in constraint_fields if constraint_field not in required_fields]

    @staticmethod
    def _compare_fields(required_fields, constraint_fields):
        """
        :param required_fields: champs requis par la configuration du modele dans le bus
        :param constraint_fields: champs contenu dans la contrainte d'unicité de la base
        :return: True si required_fields contient exactement les éléments de constraint_fields
        """
        required_fields.sort()
        constraint_fields.sort()
        return required_fields == constraint_fields

    def _get_constraint_name(self, mapping, required_fields):
        """
        cherche dans la bdd une contrainte d'unicité existante sur le modele :param mapping composée
        des champs de :param required_fields
        :return: la contrainte si trouvée sinon null
        """
        model_name = mapping.model_name.replace('.', '_')
        self.env.cr.execute(self._query_select_constraint, [model_name])
        for result_line in self.env.cr.dictfetchall():
            if self._compare_fields(required_fields, result_line['constraint_fields']):
                return result_line['constraint_name']
        return False

    def _get_error_message(self, mapping):
        required_fieds = [field.field_name for field in mapping.field_ids if field.is_migration_key]
        if not required_fieds:
            return ""
        # hack.. default_code is a product_product field linked to product_template by odoo with some black magic
        if mapping.model_name == 'product.template' and required_fieds == ['default_code']:
            mapping = self.env['bus.object.mapping'].search([('model_name', 'like', 'product.product')])

        db_constraint_name = self._get_constraint_name(mapping, required_fieds)
        nullable_fields = self._get_nullable_fields(mapping.model_name, required_fieds)

        if db_constraint_name and not nullable_fields:
            return ""

        error_message = "\n/* ----------------------- *\n" \
                        " * %s\n" \
                        " * ----------------------- */\n" % mapping.model_name
        if not db_constraint_name:
            # error_message += self._get_uniq_constraint_sql_code(mapping.model_name, required_fieds) + "\n"
            error_message += self._get_uniq_constraint_python_code(required_fieds) + "\n"
        if nullable_fields:
            for field in nullable_fields:
                # error_message += self._get_not_null_constraint_sql_code(mapping.model_name, field) + "\n"
                error_message += "'%s'.'%s' field must be 'required=True'\n" % (mapping.model_name, field)

        return error_message

    def check_models_constraints_abstract_test(self):
        """
        Si la config d'un export de modele indique une migration key alors il faut une contrainte d'unicité sur le
        champs
        Exemple: clé de migration définie sur res.country.name
            => il ne doit pas y avoir 2 res.country avec le meme name
            => name doit etre renseigné.
        """
        mappings = self.env['bus.object.mapping'].search([])
        error_message = ""
        for mapping in mappings:
            error_message += self._get_error_message(mapping)

        if error_message:
            self.fail(error_message)
