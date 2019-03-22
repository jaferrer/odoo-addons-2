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

import re
from odoo import models, api, _
from odoo.exceptions import UserError, RedirectWarning


class OpenConfigSettigns(models.TransientModel):
    _name = 'open.config.settings'

    @api.multi
    def copy(self, values):
        raise UserError(_("Configuration cannot be copied"))

    @api.model
    def default_get(self, fields):
        res = super(OpenConfigSettigns, self).default_get(fields)

        # defaults: take the corresponding default value they set
        for name, field in self._fields.iteritems():
            if name.startswith('default_') and hasattr(field, 'default_model'):
                value = self.env['ir.values'].get_default(field.default_model, name[8:])
                if value is not None:
                    res[name] = value

        # other fields: call all methods that start with 'get_default_'
        for method in dir(self):
            if method.startswith('get_default_'):
                res.update(getattr(self, method)(fields))

        return res

    @api.multi
    def execute(self):
        self.ensure_one()

        self = self.with_context(active_test=False)

        # default values fields
        for name, field in self._fields.iteritems():
            if name.startswith('default_') and hasattr(field, 'default_model'):
                if isinstance(self[name], models.BaseModel):
                    if self._fields[name].type == 'many2one':
                        value = self[name].id
                    else:
                        value = self[name].ids
                else:
                    value = self[name]
                self.env['ir.values'].sudo().set_default(field.default_model, name[8:], value)

        self.recompute()

        # other fields: execute all methods that start with 'set_'
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self.sudo(), method)()

        # Not sure what it does, and it requires the user to have some special rights
        # config = self.env['res.config'].next() or {}
        # if config.get('type') not in ('ir.actions.act_window_close',):
        #     return config

        # force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def cancel(self):
        """
          ###########################################
         # Taken straight from res.config.settings #
        ###########################################
        """
        # ignore the current record, and send the action to reopen the view
        actions = self.env['ir.actions.act_window'].search([('res_model', '=', self._name)], limit=1)
        if actions:
            return actions.read()[0]
        return {}

    @api.multi
    def name_get(self):
        """
          ###########################################
         # Taken straight from res.config.settings #
        ###########################################

        Override name_get method to return an appropriate configuration wizard
        name, and not the generated name."""
        action = self.env['ir.actions.act_window'].search([('res_model', '=', self._name)], limit=1)
        name = action.name or self._name
        return [(record.id, name) for record in self]

    @api.model
    def get_option_path(self, menu_xml_id):
        """
          ###########################################
         # Taken straight from res.config.settings #
        ###########################################

        Fetch the path to a specified configuration view and the action id to access it.

        :param string menu_xml_id: the xml id of the menuitem where the view is located,
            structured as follows: module_name.menuitem_xml_id (e.g.: "sales_team.menu_sale_config")
        :return tuple:
            - t[0]: string: full path to the menuitem (e.g.: "Settings/Configuration/Sales")
            - t[1]: int or long: id of the menuitem's action
        """
        ir_ui_menu = self.env.ref(menu_xml_id)
        return (ir_ui_menu.complete_name, ir_ui_menu.action.id)

    @api.model
    def get_option_name(self, full_field_name):
        """
          ###########################################
         # Taken straight from res.config.settings #
        ###########################################

        Fetch the human readable name of a specified configuration option.

        :param string full_field_name: the full name of the field, structured as follows:
            model_name.field_name (e.g.: "sale.config.settings.fetchmail_lead")
        :return string: human readable name of the field (e.g.: "Create leads from incoming mails")
        """
        model_name, field_name = full_field_name.rsplit('.', 1)
        return self.env[model_name].fields_get([field_name])[field_name]['string']

    @api.model_cr_context
    def get_config_warning(self, msg):
        """
          ###########################################
         # Taken straight from res.config.settings #
        ###########################################

        Helper: return a Warning exception with the given message where the %(field:xxx)s
        and/or %(menu:yyy)s are replaced by the human readable field's name and/or menuitem's
        full path.

        Usage:
        ------
        Just include in your error message %(field:model_name.field_name)s to obtain the human
        readable field's name, and/or %(menu:module_name.menuitem_xml_id)s to obtain the menuitem's
        full path.

        Example of use:
        ---------------
        from odoo.addons.base.res.res_config import get_warning_config
        raise get_warning_config(cr, _("Error: this action is prohibited. You should check the field
        %(field:sale.config.settings.fetchmail_lead)s in %(menu:sales_team.menu_sale_config)s."), context=context)

        This will return an exception containing the following message:
            Error: this action is prohibited. You should check the field Create leads from incoming mails in
            Settings/Configuration/Sales.

        What if there is another substitution in the message already?
        -------------------------------------------------------------
        You could have a situation where the error message you want to upgrade already contains a substitution. Example:
            Cannot find any account journal of %s type for this company.\n\nYou can create one in the menu: \n
            Configuration/Journals/Journals.
        What you want to do here is simply to replace the path by %menu:account.menu_account_config)s, and leave the
        rest alone.
        In order to do that, you can use the double percent (%%) to escape your new substitution, like so:
            Cannot find any account journal of %s type for this company.\n\nYou can create one in the
            %%(menu:account.menu_account_config)s.
        """
        self = self.sudo()

        # Process the message
        # 1/ find the menu and/or field references, put them in a list
        regex_path = r'%\(((?:menu|field):[a-z_\.]*)\)s'
        references = re.findall(regex_path, msg, flags=re.I)

        # 2/ fetch the menu and/or field replacement values (full path and
        #    human readable field's name) and the action_id if any
        values = {}
        action_id = None
        for item in references:
            ref_type, ref = item.split(':')
            if ref_type == 'menu':
                values[item], action_id = self.get_option_path(ref)
            elif ref_type == 'field':
                values[item] = self.get_option_name(ref)

        # 3/ substitute and return the result
        if action_id:
            return RedirectWarning(msg % values, action_id, _('Go to the configuration panel'))
        return UserError(msg % values)
