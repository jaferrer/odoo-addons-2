odoo.define('web_calendar.CalendarView_export', function (require) {
    "use strict";

    var core = require('web.core');
    var CalendarView = require('web_calendar.CalendarView');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');
    var _t = core._t;
    var _lt = core._lt;

    CalendarView.include({

        render_buttons: function($node) {
            this._super($node);
            var self=this;
            this.$buttons.on('click', 'button.o_calendar_button_export', function () {
                self.export_current_calendar();
             });
        },

        export_current_calendar: function () {

            var c = openerp.webclient.crashmanager;
            //var s = new XMLSerializer();
            //
            //var html = s.serializeToString(this.$calendar);
            //console.log(html);
            ////console.log(html.replace("width=\""+this.width+"\"","").replace("height=\""+this.height+"\"","height=\"400\"").replace("<svg ","<svg viewBox=\"0 0 "+this.width+" "+this.height+"\" "));
            //html = html.replace("width=\"" + this.width + "\"", "").replace("height=\"" + this.height + "\"", "height=\"400\"").replace("<svg ", "<svg viewBox=\"0 0 " + this.width + " " + this.height + "\" ");
            framework.blockUI();
            this.session.get_file({
                url: '/web_calendar_export/export_calendar',
                data: {
                    data: window.btoa(unescape(this.$calendar[0].innerHTML))
                },
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(c)
            });
        }

    });
});

