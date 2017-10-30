odoo.define('web_calendar.CalendarView_export', function (require) {
    "use strict";

    var core = require('web.core');
    var CalendarView = require('web_calendar.CalendarView');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');
    var _t = core._t;
    var _lt = core._lt;

    CalendarView.include({

        render_buttons: function ($node) {
            this._super($node);
            var self = this;
            this.$buttons.on('click', 'button.o_calendar_button_export', function () {
                self.export_current_calendar();
            });
        },

        export_current_calendar: function () {

            var c = openerp.webclient.crashmanager;

            var $a = this.$calendar.clone();
            $a.find(".fc-agenda-slots").parent().parent().css('height', '');
            $a.find(".fc-agenda-slots").parent().parent().css('position', 'relative');
            $a.find(".fc-agenda-days").css('position', 'absolute');
            $a.find(".fc-agenda-allday").css('position', 'relative');
            $a.find(".fc-agenda-allday").parent().css('position', 'relative');
            framework.blockUI();
            this.session.get_file({
                url: '/web_calendar_export/export_calendar',
                data: {
                    data: window.btoa(encodeURI("<div class='o_calendar_container'><div class='o_calendar_view' style='width: 100%;'><div class='o_calendar_widget fc fc-ltr'>" + $a[0].innerHTML + "</div></div></div>"))
                },
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(c)
            });
        }

    });
});

