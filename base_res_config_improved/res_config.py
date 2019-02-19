# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import models, api


class res_config_settings_improved(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _get_classified_fields(self):
        res = super(res_config_settings_improved, self)._get_classified_fields()

        if 'with_config_improved' in self.env.context:
            config = self.browse(self.env.context['with_config_improved'])
            ctx = self.env.context.copy()
            ctx.pop('with_config_improved', None)
            current_config = self.with_context(ctx).default_get(fields=[])

            res_group = res['group'][:]

            i = 0
            for name, _, _ in res_group:
                if config[name] == current_config[name]:
                    res['group'].remove(res_group[i])
                i += 1

            res_module = res['module'][:]

            i = 0
            for name, module in res_module:
                if config[name] and module.state not in ('uninstalled', 'to install', 'to upgrade'):
                    res['module'].remove(res_module[i])
                i += 1

        return res

    @api.multi
    def execute(self):
        ctx = self.env.context.copy()
        ctx.update({'with_config_improved': self.ids[0]})
        return super(res_config_settings_improved, self.with_context(ctx)).execute()
