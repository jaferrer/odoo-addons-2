odoo.define('percentage_widget', function(require) {
	"use strict";

	var field_utils = require('web.field_utils');
	var basic_fields = require('web.basic_fields');
	var field_registry = require('web.field_registry');
	var ListRenderer = require('web.ListRenderer');

	// form view
	field_utils['format']['percent'] = function(value, field, options) {
		if (value > 1){
			return '+' + ((value - 1)*100).toFixed(2) + ' %';
		} else if (0 > value > 1)  {
			return '-' + ((1 - value)*100).toFixed(2) + ' %';
		} else {
			return '0.00 %'
		}
	};

	field_utils['parse']['percent'] = field_utils.parseFloat;
	var PercentageField = basic_fields.FieldFloat.extend({
		formatType: 'percent',
	});

	field_registry.add('percent', PercentageField);

	// List View
	ListRenderer.include({

		_renderBodyCell: function (record, node, colIndex, options) {
			let result = this._super(record, node, colIndex, options);
            var name = node.attrs.name;
            var widget = node.attrs.widget;
            var field = this.state.fields[name];
            if (field && field.type === 'float' && widget && widget === 'percent') {
            	result.empty();
                var value = record.data[name];
                let option = {
                    data: record.data,
                    escape: true,
                    isPassword: 'password' in node.attrs,
                };
                var formattedValue = field_utils.format['percent'](value, field, option);
                this._handleAttributes(result, node);
                return result.html(formattedValue);
            }
            return result
        }
	});

	return {
		PercentageField: PercentageField,
	};

});
