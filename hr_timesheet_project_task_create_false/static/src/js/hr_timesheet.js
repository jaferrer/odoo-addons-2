odoo.define('hr_timesheet_project_task_create_false.sheet', function (require) {
    'use strict';

    var core = require('web.core');

    core.form_custom_registry.get('weekly_timesheet').include({

        init_add_project: function() {
            var self = this;
            self._super.apply(self, arguments);
            self.project_m2o.can_create = false;
            self.task_m2o.can_create = false;
        },
    });
});
