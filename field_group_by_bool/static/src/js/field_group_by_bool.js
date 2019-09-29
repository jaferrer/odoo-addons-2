odoo.define('field_group_by_bool.ColumnBool', function (require) {
    "use strict";

    var core = require('web.core');
    var listView = require('web.ListView');
    var list_widget_registry = core.list_widget_registry;
    var columnBinary = list_widget_registry.get('field.boolean');

    columnBinary.include({
        _format: function (row_data, options) {
            if (typeof row_data[this.id].value === 'string') {
                return listView.Column._format.bind(this, row_data, options);
            }
            return _.str.sprintf('<div class="o_checkbox"><input type="checkbox" %s disabled="disabled"/><span/></div>',
                row_data[this.id].value ? 'checked="checked"' : '');
        }
    });
    list_widget_registry.add('field.boolean', columnBinary)

});