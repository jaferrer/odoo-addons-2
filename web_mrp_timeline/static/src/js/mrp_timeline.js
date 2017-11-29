odoo.define('web_mrp_timeline.TimelineView', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var time = require('web.time');
    var session = require('web.session');
    var TimelineView = require('web_timeline.TimelineView');

    var _t = core._t;
    var QWeb = core.qweb;

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    TimelineView.include({

        init_timeline: function () {
            this._super();
            this.mode = 'custom';
            this.timeline.on('rangechanged', function (properties) {
                if (properties.byUser) {
                    localStorage.setItem('timeline_end', properties.end);
                    localStorage.setItem('timeline_start', properties.start);
                }
            });
        },

        on_scale_last_position: function () {
            var timeline_end = localStorage.getItem('timeline_end');
            var timeline_start = localStorage.getItem('timeline_start');
            console.log(timeline_start, timeline_end);
            if (!isNullOrUndef(timeline_end) && !isNullOrUndef(timeline_start)) {
                this.current_window = this.timeline.getWindow();
                this.current_window.start = timeline_start;
                this.current_window.end = timeline_end;
                this.timeline.setWindow(this.current_window);
            }
        },

        reload: function () {
            var self = this;
            $.when(this._super()).then(
                self.on_scale_last_position()
            )
        },

        on_move: function (item, callback) {
            var self = this;
            var event_start = item.start;
            var event_end = item.end;
            var group = false;
            if (item.group != -1) {
                group = item.group;
            }
            var data = {};
            // In case of a move event, the date_delay stay the same, only date_start and stop must be updated
            data[this.date_start] = time.auto_date_to_str(event_start, self.fields[this.date_start].type);
            if (this.date_stop) {
                // In case of instantaneous event, item.end is not defined
                if (event_end) {
                    data[this.date_stop] = time.auto_date_to_str(event_end, self.fields[this.date_stop].type);
                } else {
                    data[this.date_stop] = data[this.date_start]
                }
            }
            if (this.date_delay && event_end) {
                var diff_seconds = Math.round((event_end.getTime() - event_start.getTime()) / 1000);
                data[this.date_delay] = diff_seconds / 3600;
            }
            if (self.grouped_by) {
                data[self.grouped_by[0]] = group;
            }
            var id = item.evt.id;
            this.dataset.write(id, data).then(
                function () {
                    self.reload();
                }
            );
        }

    });
});