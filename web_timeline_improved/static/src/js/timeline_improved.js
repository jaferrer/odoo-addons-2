odoo.define('web_timeline_improved.TimelineView', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var time = require('web.time');
    var session = require('web.session');
    var TimelineView = require('web_timeline.TimelineView');


    TimelineView.include({

        init_timeline: function () {
            var self = this;
            let options= self._get_option_timeline();

            self.timeline = new vis.Timeline(self.$timeline.empty().get(0));
            self.timeline.setOptions(options);
            if (self.mode && self['on_scale_' + self.mode + '_clicked']) {
                self['on_scale_' + self.mode + '_clicked']();
            }
            self.timeline.on('click', self.on_click);
        },
        _get_option_timeline: function () {
            var self = this;
            let options = {
                groupOrder: self.group_order,
                editable: {
                    // add new items by double tapping
                    add: self.permissions['create'],
                    // drag items horizontally
                    updateTime: self.permissions['write'],
                    // drag items from one group to another
                    updateGroup: self.permissions['write'],
                    // delete an item by tapping the delete button top right
                    remove: self.permissions['unlink']
                },
                orientation: 'both',
                selectable: true,
                showCurrentTime: true,
                onAdd: self.on_add,
                onMove: self.on_move,
                onUpdate: self.on_update,
                onRemove: self.on_remove,
                zoomKey: this.zoomKey
            };
            if (this.mode) {
                var start = false, end = false;
                switch (this.mode) {
                    case 'day':
                        start = new moment().startOf('day');
                        end = new moment().endOf('day');
                        break;
                    case 'week':
                        start = new moment().startOf('week');
                        end = new moment().endOf('week');
                        break;
                    case 'month':
                        start = new moment().startOf('month');
                        end = new moment().endOf('month');
                        break;
                }
                if (end && start) {
                    options['start'] = start;
                    options['end'] = end;
                } else {
                    this.mode = 'fit';
                }
            }

            if (this.fields_view.arch.attrs.exclude_hours) {
                let tab_hours = this.fields_view.arch.attrs.exclude_hours.split("-");
                let start_hours = tab_hours[0];
                let end_hours = tab_hours[1];
                console.log(start_hours, end_hours);
                options.hiddenDates = [
                    {
                        start: start.hours(end_hours).format("YYYY-MM-DD HH:00:00"),
                        end: start.add(1, 'day').hours(start_hours).format("YYYY-MM-DD HH:00:00"),
                        repeat:"daily"
                    },
                ];
            }
            if (this.fields_view.arch.attrs.min_zoom) {
                options.zoomMin = this.fields_view.arch.attrs.min_zoom * 60000;
            }
            console.log(options);
            return options
        },

        get_fields_to_read:function(n_group_bys){
            self = this;
            var fields = _.map(["date_start", "date_delay", "date_stop", "progress", "color_field"], function (key) {
                return self.fields_view.arch.attrs[key] || '';
            });

            fields = _.compact(_.uniq(fields
                .concat(_.map(this.fields_view.fields, function (field) {
                    return field.__attrs.name;
                }))
                .concat(_.map(this.colors, function (color) {
                    if (color[1].expressions !== undefined) {
                        return color[1].expressions[0].value
                    }
                }))
                .concat(n_group_bys)));
            return fields
        },

        do_search: function (domains, contexts, group_bys) {
            var self = this;
            self.last_domains = domains;
            self.last_contexts = contexts;
            // select the group by
            var n_group_bys = [];
            if (this.fields_view.arch.attrs.default_group_by) {
                n_group_bys = this.fields_view.arch.attrs.default_group_by.split(',');
            }
            if (group_bys.length) {
                n_group_bys = group_bys;
            }
            self.last_group_bys = n_group_bys;
            // gather the fields to get
            var fields = this.get_fields_to_read(n_group_bys);
            return $.when(this.has_been_loaded).then(function () {
                return self.dataset.read_slice(fields, {
                    domain: domains,
                    context: contexts
                }).then(function (data) {
                    return self.on_data_loaded(data, n_group_bys);
                });
            });
        },

        parse_colors : function () {
            this._super();
            if (! this.hasOwnProperty('colors')) {
                this.colors = [];
            }

        },

        event_data_transform : function (evt) {
            let result = this._super(evt);
            if (evt.hasOwnProperty(this.fields_view.arch.attrs.color_field)) {
                result.style = 'background-color: ' + evt[this.fields_view.arch.attrs.color_field] + ';'
            }
            console.log(evt);
            console.log(result);
            return result;
        }
    })
})
;