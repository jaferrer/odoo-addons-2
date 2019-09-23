odoo.define('web_kanban_fold.KanbanColumnFold', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var _t = core._t;
    // var time = require('web.time');
    // var session = require('web.session');
    var form_common = require('web.form_common');
    var KanbanColumn = require('web_kanban.Column');
    var KanbanView = require('web_kanban.KanbanView');

    KanbanView.include({
        init: function () {
            this._super.apply(this, arguments);
            this.on_edit_stage = this.fields_view.arch.attrs.on_edit_stage;
        },

        get_column_options: function () {
            let result = this._super.apply(this, arguments);
            result.on_edit_stage = this.on_edit_stage;
            return result
        }
    });


    KanbanColumn.include({

        init: function (parent, group_data, options, record_options) {
            this._super(parent, group_data, options, record_options);
            this.on_edit_stage = options.on_edit_stage
        },

        do_reload: function() {
            this.trigger_up('kanban_reload');
        },

        edit_column: function (event) {
            event.preventDefault();
            self = this;
            if (this.on_edit_stage) {
                console.log('on_edit_stage');
                self.do_action(self.on_edit_stage, {
                    on_close: self.do_reload.bind(self),
                    additional_context: {
                        active_model: this.relation,
                        active_id: this.id,
                        active_ids: [this.id],
                    },
                    res_id:this.id
                });
            } else{
                this._super(event)
            }
        },
    })
})
;