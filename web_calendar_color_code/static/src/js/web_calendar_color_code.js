odoo.define('web_calendar_color_code.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('web_calendar.CalendarView');

    CalendarView.include({
        init: function () {
            this._super.apply(this, arguments);
            var attrs = this.fields_view.arch.attrs;
            this.color_code_field = attrs.color_code;
        },
        event_data_transform: function (evt) {
            var r = this._super(evt);

            var color_code = evt[this.color_code_field];
            if (color_code !== undefined) {
                r.color = color_code;
            }
            return r;
        }
    });
});
