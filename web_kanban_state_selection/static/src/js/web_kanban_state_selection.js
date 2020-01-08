odoo.define('web_kanban_state_selection.ListView', function (require) {
    "use strict";

    var core = require('web.core');
    var ListView = require('web.ListView');
    var KanbanWidgets = require('web_kanban.widgets');

    var list_widget_registry = core.list_widget_registry;

    var KanbanSelection = ListView.Column.extend({
        _format: function (row_data, options) {
            var state_name = '';
            var name_val = row_data[this.id].value;
            var state_class = '';

            if (row_data[this.id].value === 'normal') {
                state_name = row_data[this.id].value;
            } else if (row_data[this.id].value === 'done') {
                state_class = 'oe_kanban_status_green';
                state_name = row_data[this.id].value;
            } else {
                state_class = 'oe_kanban_status_red';
                state_name = row_data[this.id].value;
            }

            return _.template(
                '<div class="btn-group o_kanban_selection"><a href="#" data-toggle="dropdown"><span class="oe_kanban_status <%-state_class%>"/></a></div>')({
                name_val: name_val,
                state_class: state_class,
                state_name: state_name,
            });
        }
    });


    list_widget_registry.add('field.kanban_state_selection', KanbanSelection);

    KanbanWidgets.registry.get('kanban_state_selection').include({
        prepare_dropdown_selection: function () {
            if (this.parent.values.stage_id) {
                return this._super();
            }
            var self = this;
            var _data = [];
            _.map(self.field.selection || [], function (res) {
                var value = {
                    'name': res[0],
                    'tooltip': res[1],
                };
                if (res[0] === 'normal') {
                    value.state_name = res[1];
                } else if (res[0] === 'done') {
                    value.state_class = 'oe_kanban_status_green';
                    value.state_name = res[1];
                } else {
                    value.state_class = 'oe_kanban_status_red';
                    value.state_name = res[1];
                }
                _data.push(value);
            });
            return _data;
        },
    })

});
