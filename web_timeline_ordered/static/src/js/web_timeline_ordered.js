odoo.define('web_timeline_ordered.TimelineView', function (require) {
    "use strict";

    var core = require('web.core');
    var form_common = require('web.form_common');
    var Model = require('web.DataModel');
    var time = require('web.time');
    var View = require('web.View');
    var widgets = require('web_calendar.widgets');
    var _ = require('_');
    var $ = require('$');

    var _t = core._t;
    var _lt = core._lt;
    var QWeb = core.qweb;

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    var TimelineView = require("web_timeline.TimelineView");
    TimelineView.include({
        view_loading: function (fv) {
            /* xml view timeline options */
            var attrs = fv.arch.attrs;
            var self = this;
            this.fields_view = fv;
            this.parse_colors();
            this.$timeline = this.$el.find(".oe_timeline_widget");
            this.$el.find(".oe_timeline_button_today").click($.proxy(this.on_today_clicked, this));
            this.$el.find(".oe_timeline_button_scale_day").click($.proxy(this.on_scale_day_clicked, this));
            this.$el.find(".oe_timeline_button_scale_week").click($.proxy(this.on_scale_week_clicked, this));
            this.$el.find(".oe_timeline_button_scale_month").click($.proxy(this.on_scale_month_clicked, this));
            this.$el.find(".oe_timeline_button_scale_year").click($.proxy(this.on_scale_year_clicked, this));
            this.$el.find(".oe_timeline_button_scale_last_position").click($.proxy(this.on_scale_last_position, this));
            this.$el.find(".oe_timeline_button_refresh_with_last_position").click($.proxy(this.refresh_with_last_position, this));
            this.current_window = {
                start: new moment(),
                end: new moment().add(24, 'hours'),
            }

            this.info_fields = [];

            if (!attrs.date_start) {
                throw new Error(_t("Timeline view has not defined 'date_start' attribute."));
            }

            this.$el.addClass(attrs['class']);

            this.name = fv.name || attrs.string;
            this.view_id = fv.view_id;
            this.mode = attrs.mode;
            this.date_start = attrs.date_start;
            this.date_stop = attrs.date_stop;
            this.order_by = (attrs.order_by == undefined) ? "id" : attrs.order_by;


            if (!isNullOrUndef(attrs.quick_create_instance)) {
                self.quick_create_instance = 'instance.' + attrs.quick_create_instance;
            }

            // If this field is set ot true, we don't open the event in form
            // view, but in a popup with the view_id passed by this parameter
            if (isNullOrUndef(attrs.event_open_popup) || !_.str.toBoolElse(attrs.event_open_popup, true)) {
                this.open_popup_action = false;
            } else {
                this.open_popup_action = attrs.event_open_popup;
            }

            this.fields = fv.fields;

            for (var fld = 0; fld < fv.arch.children.length; fld++) {
                this.info_fields.push(fv.arch.children[fld].attrs.name);
            }

            var fields_get = new Model(this.dataset.model)
                .call('fields_get')
                .then(function (fields) {
                    self.fields = fields;
                });
            var unlink_check = new Model(this.dataset.model)
                .call("check_access_rights", ["unlink", false])
                .then(function (unlink_right) {
                    self.unlink_right = unlink_right;
                });
            var edit_check = new Model(this.dataset.model)
                .call("check_access_rights", ["write", false])
                .then(function (write_right) {
                    self.write_right = write_right;

                });
            var init = function () {
                self.init_timeline().then(function () {
                    $(window).trigger('resize');
                    self.trigger('timeline_view_loaded', fv);

                    self.ready.resolve();
                });

                self.timeline.on('rangechanged', function (properties) {
                    if (properties.byUser) {
                        localStorage.setItem('timeline_end', properties.end);
                        localStorage.setItem('timeline_start', properties.start);
                    }
                });


                self.timeline.setOptions({
                    order: function (a, b) {
                        // order by fields supplier in 'order_by'
                        (attrs.order_by == undefined) ? "id" : attrs.order_by
                        var a1 = a[self.order_by];
                        if (a[self.order_by] == undefined) {
                            a1 = a.evt[self.order_by];
                            if (a1 instanceof Array) {
                                a1 = a1[0]
                            }
                        }
                        if (a1 == false) {
                            a1 = 0
                        }
                        var b1 = b[self.order_by];
                        if (b[self.order_by] == undefined) {
                            b1 = b.evt[self.order_by];
                            if (b1 instanceof Array) {
                                b1 = b1[0]
                            }
                        }
                        if (b1 == false) {
                            b1 = 0
                        }
                        return b1 - a1;
                    }
                });


            };
            return $.when(self.fields_get, self.get_perm('unlink'), self.get_perm('write'), self.get_perm('create')).then(init);
        },
        on_scale_last_position: function(){
            var timeline_end = localStorage.getItem('timeline_end');
            var timeline_start = localStorage.getItem('timeline_start');
            if (!isNullOrUndef(timeline_end) && !isNullOrUndef(timeline_start)) {
                this.current_window = {
                    start: moment(timeline_start),
                    end: moment(timeline_end)
                }
                this.timeline.setWindow(this.current_window);

            }
        },
        refresh_with_last_position: function(){
            var self = this;
            $.when(this.reload()).then(function(){
                self.on_scale_last_position()
            })
        },
        list_parameters: ["date_start", "date_delay", "date_stop", "progress", "order_by"],
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
            var fields = _.compact(_.map(self.list_parameters, function (key) {
                return self.fields_view.arch.attrs[key] || '';
            }));

            fields = _.uniq(fields.concat(_.pluck(this.colors, "field").concat(n_group_bys)));
            return $.when(this.has_been_loaded).then(function () {
                return self.dataset.read_slice(fields, {
                    domain: domains,
                    context: contexts
                }).then(function (data) {
                    return self.on_data_loaded(data, n_group_bys);
                }).then(function(){
                    if(contexts.set_last_position)
                    {
                        this.on_scale_last_position();
                    }
                })
            });
        },
        event_data_transform: function (evt) {
            var self = this;
            var date_start = new moment();
            var date_stop = new moment();

            var date_delay = evt[this.date_delay] || 1.0,
                all_day = this.all_day ? evt[this.all_day] : false,
                res_computed_text = '',
                the_title = '',
                attendees = [];

            if (!all_day) {
                date_start = time.auto_str_to_date(evt[this.date_start]);
                date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop]) : null;
            }
            else {
                date_start = time.auto_str_to_date(evt[this.date_start].split(' ')[0], 'start');
                date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop].split(' ')[0], 'stop') : null;
            }

            if (!date_start) {
                date_start = new moment();
            }
            if (!date_stop) {
                date_stop = moment(date_start).add(date_delay, 'hours').toDate();
            }
            var group = evt[self.last_group_bys[0]];
            if (group) {
                group = _.first(group);
            } else {
                group = -1;
            }
            _.each(self.colors, function (color) {
                if (eval("'" + evt[color.field] + "' " + color.opt + " '" + color.value + "'"))
                    self.color = color.color;
            });
            var r = {
                'start': date_start,
                'end': date_stop,
                'content': evt.__name != undefined ? evt.__name : evt.display_name,
                'id': evt.id,
                'group': group,
                'evt': evt,
                'style': 'background-color: ' + self.color + ';',
                'className': evt.macro_tache ? "macro_tache" : "", // added to fix on top macro tache
            };
            self.color = undefined;
            return r;
        },
    })

});