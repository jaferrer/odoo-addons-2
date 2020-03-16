odoo.define('web_tree_fix.web_tree_fix', function (require) {

    var ListRenderer = require('web.ListRenderer');
    var field_utils = require('web.field_utils');

    ListRenderer.include({

        _renderBodyCell: function (record, node, colIndex, options) {
            let result = this._super(record, node, colIndex, options);
            var name = node.attrs.name;
            var field = this.state.fields[name];
            if (field && field.type === "float") {
                result.empty();
                var value = record.data[name];
                let option = {
                    data: record.data,
                    escape: true,
                    isPassword: 'password' in node.attrs,
                    digits: JSON.parse(node.attrs.digits || JSON.stringify(field.digits || [16, 2])),
                };
                var formattedValue = field_utils.format[field.type](value, field, option);
                this._handleAttributes(result, node);
                return result.html(formattedValue);
            }
            return result
        }
    });

});