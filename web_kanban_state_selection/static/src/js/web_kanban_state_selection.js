odoo.define('web_kanban_state_selection.ListView', function (require) {
    "use strict";

    var core = require('web.core');
    var ListView = require('web.ListView');

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

    list_widget_registry
    .add('field.kanban_state_selection', KanbanSelection);
});
