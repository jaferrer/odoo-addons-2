# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _


class AbstractLiveI10N(models.AbstractModel):
    _name = 'live.l10n'
    _inherit = 'on_change.action'
    _current_model = _name

    @api.multi
    def _action_on_change(self, field_name, field_value):
        if not self.exists():
            return {}
        model_name = self._name
        model_id = self.id
        for key, value in self._inherits.iteritems():
            if field_name in self.env[key]._fields:
                model_name = key
                model_id = getattr(self, value).id
        if self.env[model_name]._fields[field_name].type != 'char':
            return {}

        ctx = dict(self.env.context)
        ctx['translate_field'] = field_name
        ctx['translate_field_value'] = field_value
        ctx['model_translate_field'] = model_name
        ctx['model_id_translate'] = model_id
        self.env['ir.translation'].translate_fields(model_name, model_id, field=field_name)
        return {
            'name': _('Translation'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'live.l10n.ir.translation',
            'domain': [],
            'context': ctx,
            'views': [[False, 'form']],
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _has_onchange(self, field, other_fields):
        res = super(AbstractLiveI10N, self)._has_onchange(field, other_fields)
        if field.type == 'char':
            res = field.translate or res
        return res


class IrTranslationLiveEdit(models.TransientModel):
    _name = 'live.l10n.ir.translation'

    line_translate_ids = fields.One2many('live.l10n.ir.translation.line', 'live_translate_id', u"Lines of translate")

    @api.model
    def default_get(self, fields):
        result = super(IrTranslationLiveEdit, self).default_get(fields)
        line_translate_ids = {}
        name_filter = '%s,%s' % (self.env.context['model_translate_field'], self.env.context['translate_field'])

        for lang in self.env['ir.translation'].search(
                [('name', '=', name_filter), ('res_id', '=', self.env.context['model_id_translate'])]):
            lang_value = lang.value
            if self.env.user.lang == lang.lang:
                lang_value = self.env.context['translate_field_value']
            line_translate_ids[lang.lang] = {
                'line_id': lang.id,
                'lang': lang.lang,
                'lang_value': lang_value
            }
            lang_src = lang.source
            if self.env.user.lang == 'en_US':
                lang_src = self.env.context['translate_field_value']
            line_translate_ids['en_US'] = {
                'line_id': lang.id,
                'lang': 'en_US',
                'lang_value': lang_src,
            }
        result.update(line_translate_ids=line_translate_ids.values())
        return result

    @api.multi
    def apply_change(self):
        self.ensure_one()
        en_line = self.line_translate_ids.filtered(lambda e: e.lang == 'en_US')
        for lang in self.env['ir.translation'].browse(self.line_translate_ids.mapped('line_id')):
            lang.source = en_line.lang_value
            lang.value = self.line_translate_ids\
                .filtered(lambda e: e.line_id == lang.id)\
                .filtered(lambda e: e.lang == lang.lang)\
                .lang_value


class IrTranslationLiveEditLine(models.TransientModel):
    _name = 'live.l10n.ir.translation.line'

    live_translate_id = fields.Many2one('live.l10n.ir.translation', u"Id live.i10n.ir.translation")
    line_id = fields.Integer(u"Id line ir_translation")
    lang = fields.Char(u"Lang", readonly=True)
    lang_value = fields.Char(u"Value")
