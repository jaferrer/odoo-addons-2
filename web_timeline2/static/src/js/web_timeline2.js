/* Odoo web_timeline
 * Copyright 2020 Ndp Systemes
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

_.str.toBoolElse = function (str, elseValues, trueValues, falseValues) {
    var ret = _.str.toBool(str, trueValues, falseValues);
    if (_.isUndefined(ret)) {
        return elseValues;
    }
    return ret;
};

odoo.define('web_timeline2.TimelineView', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var form_common = require('web.form_common');
    var Model = require('web.DataModel');
    var time = require('web.time');
    var View = require('web.View');
    var widgets = require('web_calendar.widgets');
    var session = require('web.session');
    const formats = require('web.formats')

    var _t = core._t;
    var _lt = core._lt;

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    var TimelineView = View.extend({
            template: "Timeline2.View",
            display_name: _lt('Timeline'),
            icon: 'fa-clock-o',
            quick_create_instance: widgets.QuickCreate,

            init: function (parent, dataset, view_id, options) {
                const result = this._super.apply(this, arguments);
                this.permissions = {};
                this.grouped_by = false;
                this.colors = [];
                this.groups = {};
                this.visGroups = new vis.DataSet()
                this.visData = new vis.DataSet()
                this._parse_attrs(this.fields_view.arch.attrs);
                return result
            },

            _parse_attrs: function (attrs) {
                if (!attrs.date_start) {
                    throw new Error(_t("Timeline view has not defined 'date_start' attribute."));
                }
                this.overlap_field = attrs['overlap_field']
                this.readonly_field = attrs['readonly_field']
                this.delegate_model_field = attrs['delegate_model_field']

                this.parse_colors(attrs.colors)

                this.date_start = attrs.date_start;
                this.date_stop = attrs.date_stop;
                this.date_delay = attrs.date_delay;
                this.no_period = this.date_start === this.date_stop;

                this.event_type = attrs.field_event_type; //The field used to determine the type of the timeline event

                this.color_field = attrs.color_field;
                this.update_group = utils.toBoolElse(attrs.update_group || '', true);
                this.update_time = utils.toBoolElse(attrs.update_time || '', true);
                this.create = utils.toBoolElse(attrs.create || '', true);
                this.unlink = utils.toBoolElse(attrs.unlink || '', true);
                this.editable = utils.toBoolElse(attrs.editable || '', true);

                this.zoomKey = attrs.zoomKey || '';
                this.mode = attrs.mode || attrs.default_window || 'fit';
                this.snapTime = attrs.minute_snap;
                this.min_zoom = attrs.min_zoom;
                this.max_zoom = attrs.max_zoom;
                this.axis = attrs.axis;

                this.visibleFrameQweb = true;
                this.tooltipOnItemUpdateTimeFormat = true;

                if (!isNullOrUndef(attrs.quick_create_instance)) {
                    this.quick_create_instance = 'instance.' + attrs.quick_create_instance;
                }

                // If this field is set ot true, we don't open the event in form
                // view, but in a popup with the view_id passed by this parameter
                if (isNullOrUndef(attrs.event_open_popup) || !_.str.toBoolElse(attrs.event_open_popup, true)) {
                    this.open_popup_action = false;
                } else {
                    this.open_popup_action = attrs.event_open_popup;
                }

            },

            get_perm: function (name) {
                if (this.permissions[name]) {
                    return $.when(this.permissions[name]);
                } else {
                    return new Model(this.perm_model)
                        .call("check_access_rights", [name, false])
                        .then((value) => {
                            this.permissions[name] = value;
                            return value;
                        });
                }
            },

            parse_colors: function (colors) {
                if (colors) {
                    this.colors = _(colors.split(';')).chain()
                        .compact()
                        .map(function (color_pair) {
                            const pair = color_pair.split(':');
                            const color = pair[0];
                            const expr = pair[1];
                            return [color, py.parse(py.tokenize(expr)), expr];
                        }).value();
                }
            },

            start: function () {
                var self = this;
                var attrs = this.fields_view.arch.attrs;
                var fv = this.fields_view;

                this.parse_colors();
                this.$timeline = this.$el.find(".oe_timeline2_widget");
                this.$(".oe_timeline_button_today").click(this.proxy(this.on_today_clicked));
                this.$(".oe_timeline_button_scale_day").click(this.proxy(this.on_scale_day_clicked));
                this.$(".oe_timeline_button_scale_week").click(this.proxy(this.on_scale_week_clicked));
                this.$(".oe_timeline_button_scale_month").click(this.proxy(this.on_scale_month_clicked));
                this.$(".oe_timeline_button_scale_year").click(this.proxy(this.on_scale_year_clicked));
                this.current_window = {
                    start: new moment(),
                    end: new moment().add(24, 'hours')
                };

                this.$el.addClass(attrs['class']);

                this.info_fields = [];
                this.fields = fv.fields;

                for (var fld = 0; fld < fv.arch.children.length; fld++) {
                    this.info_fields.push(fv.arch.children[fld].attrs.name);
                }
                this._super.apply(this, self);

                return new Model(this.dataset.model)
                    .call('fields_get')
                    .then((fields) => {
                        self.fields = fields;
                        this.perm_model = this.dataset.model
                        if (this.delegate_model_field) {
                            const field_def = this.fields[this.delegate_model_field]
                            if (field_def.type !== 'many2one') throw Error('The delegate must be a Many2one not a ' + field_def.type);
                            this.perm_model = field_def.relation
                        }
                        return $.when(
                            self.get_perm('unlink'),
                            self.get_perm('write'),
                            self.get_perm('create')
                        ).then(function () {
                            self.init_timeline();
                            $(window).trigger('resize');
                            self.trigger('timeline_view_loaded', fv);
                        })

                    });
            },
            _get_option_timeline: function () {
                let options = {
                    groupOrder: this.group_order,
                    selectable: true,
                    showCurrentTime: true,
                    showMinorLabels: true,
                    orientation: this.headerOrientation || 'both',
                    onAdd: this.on_add,
                    onMove: this.on_move,
                    onUpdate: this.on_update,
                    onRemove: this.on_remove,
                    zoomKey: this.zoomKey,
                    stack: true,
                    stackSubgroups: true,
                };
                if (this.axis) {
                    const axis = this.axis.split(':')
                    options.timeAxis = {
                        scale: axis[1] || 'hour',
                        step: parseInt(axis[0]),
                    }
                }
                if (this.editable) {
                    options.editable = {
                        // add new items by double tapping
                        add: this.create && this.permissions['create'],
                        // drag items horizontally
                        updateTime: this.update_time && this.permissions['write'],
                        // drag items from one group to another
                        updateGroup: this.update_group && this.permissions['write'],
                        // delete an item by tapping the delete button top right
                        remove: this.unlink && this.permissions['unlink']
                    }
                } else {
                    options.editable = false
                }
                if (this.snapTime) {
                    options.snap = (date, scale, step) => {
                        const hour = parseInt(this.snapTime) * 60 * 1000;
                        return Math.round(date / hour) * hour;
                    }
                }
                if (this.visibleFrameQweb) {
                    const template = 'Timeline2.DefaultItemTemplate';
                    options.visibleFrameTemplate = function (item, element, data) {
                        return core.qweb.render(template, {
                            item: item,
                            element: element,
                            data: data
                        })
                    }
                }
                if (this.tooltipOnItemUpdateTimeFormat) {
                    const format = 'DD/MM/YYYY HH:mm';
                    options.tooltipOnItemUpdateTime = {
                        template: function (item) {
                            let content = `Début: ` + moment(item.start).format(format);
                            if (this.data.end) {
                                content += `<br> Fin: ` + moment(item.end).format(format);
                            }
                            return content;
                        }
                    }
                }
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
                        start = new moment().startOf('day');
                    }
                }

                if (this.fields_view.arch.attrs.exclude_hours) {
                    let tab_hours = this.fields_view.arch.attrs.exclude_hours.split("-");
                    let start_hours = tab_hours[0];
                    let end_hours = tab_hours[1];
                    let dstart = new moment(start);
                    if (dstart !== false) {
                        options.hiddenDates = [
                            {
                                start: dstart.hours(end_hours).format("YYYY-MM-DD HH:00:00"),
                                end: new moment(dstart).add(1, 'day').hours(start_hours).format("YYYY-MM-DD HH:00:00"),
                                repeat: "daily"
                            },
                        ];
                    }
                }
                if (this.min_zoom) {
                    options.zoomMin = this.min_zoom * 60000;
                }
                if (this.max_zoom) {
                    options.zoomMax = this.max_zoom * 60000;
                }
                return options
            },

            init_timeline: function () {
                this.timeline = new vis.Timeline(this.$timeline.empty().get(0));
                this.timeline.setOptions(this._get_option_timeline());
                this.timeline.setGroups(this.visGroups);
                this.timeline.setItems(this.visData);
                if (this.mode && this['on_scale_' + this.mode + '_clicked']) {
                    this['on_scale_' + this.mode + '_clicked']();
                }
                this.timeline.on('click', this.on_click.bind(this));
            },

            group_order: function (grp1, grp2) {
                // display non grouped elements first
                if (grp1.id === -1) {
                    return -1;
                }
                if (grp2.id === -1) {
                    return +1;
                }
                return grp1.id - grp2.id;
            },

            _get_color_for_item(evt) {
                if (evt.hasOwnProperty(this.color_field)) {
                    return evt[this.color_field];
                }
                let color;
                const context = _.extend({}, evt, {
                    uid: session.uid,
                    current_date: moment().format('YYYY-MM-DD')
                });
                for (let i = 0, len = this.colors.length; i < len; ++i) {
                    if (py.PY_isTrue(py.evaluate(pair[1], context))) {
                        color = pair[0];
                    }
                }
                return color;
            },
            /* Transform Odoo event object to timeline event object */
            event_data_transform: function (evt) {
                let date_start = new moment();
                let date_stop;

                let date_delay = evt[this.date_delay] || false;
                const all_day = this.all_day ? evt[this.all_day] : false;

                if (!all_day) {
                    date_start = time.auto_str_to_date(evt[this.date_start]);
                    date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop]) : null;
                } else {
                    date_start = time.auto_str_to_date(evt[this.date_start].split(' ')[0], 'start');
                    if (this.no_period) {
                        date_stop = date_start
                    } else {
                        date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop].split(' ')[0], 'stop') : null;
                    }
                }
                if (!date_start) {
                    date_start = new moment();
                }
                if (!date_stop && date_delay) {
                    date_stop = moment(date_start).add(date_delay, 'hours').toDate();
                }
                let color = this._get_color_for_item(evt);
                var r = {
                    'start': date_start,
                    'content': evt.display_name,
                    'title': evt.display_name,
                    'id': evt.id,
                    'evt': evt,
                    'style': 'background-color: ' + color + ';'
                };
                if (this.event_type && evt.hasOwnProperty(this.event_type)) {
                    r.type = evt[this.event_type];
                }
                // Check if the event is instantaneous, if so, display it with a point on the timeline (no 'end')
                if (date_stop && !moment(date_start).isSame(date_stop)) {
                    r.end = date_stop;
                    if (r.type !== 'background') {
                        r.content = moment(date_start).format('HH:mm') + ' - ' + moment(date_stop).format('HH:mm')
                        r.title += ' : ' + r.content
                    }
                }
                return r;
            },

            get_fields_to_read: function (n_group_bys) {
                self = this;
                const base_field = ["date_start", "date_delay", "date_stop", "progress", "color_field",
                    "event_type", "overlap_field"]
                var fields = _.map(base_field, function (key) {
                    return self.fields_view.arch.attrs[key] || '';
                });

                fields = _.compact(_.uniq(fields
                    .concat(["display_name"])
                    .concat(Object.entries(self.fields).filter(([_, value]) => value.searchable).map(([k, _]) => k)))
                    .concat(_.map(this.colors, function (color) {
                        if (color[1].expressions !== undefined) {
                            return color[1].expressions[0].value
                        }
                    }))
                    .concat(n_group_bys));
                return fields
            },

            do_search: function (domains, contexts, group_bys) {
                var self = this;
                this.visData.clear();
                this.visGroups.clear();
                this.groups = {};
                this.visGroups.add({
                    id: -1,
                    content: "-"
                })

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
                // self.convert_data_to_timeline(res, ...it)
                self.last_group_bys = n_group_bys;
                this.fields_used = this.get_fields_to_read(n_group_bys);
                return this._internal_do_search(this.last_domains, this.last_contexts, this.last_group_bys, false);
            },

            _internal_do_search: function (domains, contexts, group_bys, updating) {
                return this.dataset._model.query(this.fields_used)
                    .filter(domains)
                    .context({...contexts, group_by_no_leaf: true})
                    .lazy(false)
                    .group_by(_.first(group_bys))
                    .then(result => {
                        $.when.apply(this, result.map(res => {
                            return this.dataset._model
                                .query(this.fields_used)
                                .context(res.model.context())
                                .filter(res.model.domain())
                                .all()
                                .then((events) => {
                                    return this.convert_data_to_timeline(res, events, updating);
                                })
                        })).then(function () {
                        })
                    });
            },

            reload: function () {
                var self = this;
                if (this.last_domains !== undefined) {
                    self.current_window = self.timeline.getWindow();
                    return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
                }
            },

            convert_data_to_timeline(grouping, events, updating) {

                let grouped_on = grouping.attributes.grouped_on;
                let value = grouping.attributes.value;
                let label = value;
                if (Array.isArray(grouping.attributes.grouped_on)) {
                    grouped_on = grouping.attributes.grouped_on[0]
                }
                let grp_id = value || -1
                if (Array.isArray(value)) {
                    grp_id = value[0];
                    label = value[1];
                }
                this.groups[grp_id] = {...grouping};
                const subgroupStack = {}
                subgroupStack["backgroud_stacked"] = true;
                subgroupStack["backgroud_unstacked"] = false;
                subgroupStack["range_stacked"] = true;
                subgroupStack["range_unstacked"] = false;
                const dataVisGrp = {
                    ...this.groups[grp_id] || {},
                    id: grp_id,
                    content: value ? label : _t("Undefined"),
                }
                if (this.overlap_field) {
                    dataVisGrp['subgroupStack'] = subgroupStack;
                    dataVisGrp['subgroupOrder'] = function (a, b) {
                        return a.subgroupOrder - b.subgroupOrder;
                    };
                }
                if (!this.visGroups.get(grp_id)) {
                    this.visGroups.add(dataVisGrp)
                }

                events.filter(evt => evt[self.date_start]).forEach((evt) => {
                        const data = self.event_data_transform(evt)
                        const data_type = (data.type || 'range')
                        const suffix = evt[this.overlap_field] ? "stacked" : "unstacked"
                        const subgroup = data_type + "_" + suffix;
                        const visEvt = {
                            ...data,
                            group: grp_id,
                        };
                        if (data_type !== 'background' && this.overlap_field) {
                            visEvt["subgroup"] = subgroup;
                            visEvt["subgroupOrder"] = suffix === 'stacked' ? 10 : 100;
                        }
                        if (!updating) {
                            this.visData.add(visEvt);
                        } else {
                            this.visData.update(visEvt);
                        }
                    }
                );


            },

            do_show: function () {
                this.do_push_state({});
                return this._super();
            },

            is_action_enabled: function (action) {
                if (action === 'create' && !this.options.creatable) {
                    return false;
                }
                return this._super(action);
            },

            create_completed: function (id) {
                var self = this;
                this.dataset.ids = this.dataset.ids.concat([id]);
                this.dataset.trigger("dataset_changed", id);
                this.dataset.read_ids([id], Object.keys(this.fields)).done(function (records) {
                    var new_event = self.event_data_transform(records[0]);
                    this.visData.add(new_event)
                });
            },

            on_add: function (item, callback) {
                var self = this;
                var context = this.dataset.get_context();
                // Initialize default values for creation
                var default_context = {};
                default_context['default_'.concat(this.date_start)] = item.start;
                if (this.date_delay) {
                    default_context['default_'.concat(this.date_delay)] = 1;
                }
                if (this.date_stop) {
                    default_context['default_'.concat(this.date_stop)] = moment(item.start).add(1, 'hours').toDate();
                }
                if (item.group > 0) {
                    default_context['default_'.concat(this.last_group_bys[0])] = item.group;
                }
                context.add(default_context);
                // Show popup
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);
                    const dialog = new form_common.FormViewDialog(this, {
                        res_model: field_def.relation,
                        context: {...this.dataset.get_context(), ...context},
                        view_id: parseInt(this.open_popup_action),
                        create_function: function (data, options) {
                            return this.dataset._model.call('delegate_create', [
                                {
                                    'delegate_field': this.delegate_model_field,
                                    'field_used': this.fields_used,
                                    'delegate_relation': field_def.relation,
                                    'delegate_data': data,
                                }
                            ], {context: context}).then(result => {
                                if (!result || !Array.isArray(result) || !result.length) return callback(null)
                                this.visData.remove(result);
                                return this._internal_do_search(
                                    [...this.last_domains, [this.delegate_model_field, '=', id]],
                                    this.last_contexts,
                                    this.last_group_bys,
                                    true
                                )
                            }).fail(error => callback(null));
                        }.bind(this),
                    }).open();
                    dialog.on('create_completed', this, () => dialog.destroy());
                } else {
                    var dialog = new form_common.FormViewDialog(this, {
                        res_model: this.dataset.model,
                        res_id: null,
                        context: context,
                        view_id: +this.open_popup_action
                    }).open();
                    dialog.on('create_completed', this, this.create_completed);
                    dialog.on('create_completed', this, () => dialog.destroy());
                }
                return false;
            },

            write_completed: function (id) {
                this.dataset.trigger("dataset_changed", id);
                this.current_window = this.timeline.getWindow();
                this.reload();
                this.timeline.setWindow(this.current_window);
            },

            on_update: function (item, callback) {
                var id = item.evt.id;
                var title = item.evt.__name;

                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);
                    id = item.evt[this.delegate_model_field][0]
                    title = item.evt[this.delegate_model_field][1]

                    const dialog = new form_common.FormViewDialog(this, {
                        res_model: field_def.relation,
                        res_id: id,
                        context: this.dataset.get_context(),
                        title: title,
                        view_id: parseInt(this.open_popup_action),
                        write_function: function (id, data, options) {
                            return this.dataset._model.call('delegate_write', [
                                [item.evt.id],
                                {
                                    'delegate_field': this.delegate_model_field,
                                    'delegate_id': id,
                                    'field_used': this.fields_used,
                                    'delegate_relation': field_def.relation,
                                    'delegate_data': data,
                                }
                            ]).then(result => {
                                if (!result || !Array.isArray(result) || !result.length) return callback(null);
                                this.visData.remove(result);
                                return this._internal_do_search(
                                    [...this.last_domains, [this.delegate_model_field, '=', id]],
                                    this.last_contexts,
                                    this.last_group_bys,
                                    true
                                )
                            }).fail(error => callback(null));
                        }.bind(this),
                    }).open();
                    dialog.on('write_completed', this, () => dialog.destroy());
                } else if (this.open_popup_action) {
                    var dialog = new form_common.FormViewDialog(this, {
                        res_model: this.dataset.model,
                        res_id: parseInt(id).toString() == id ? parseInt(id) : id,
                        context: this.dataset.get_context(),
                        title: title,
                        view_id: +this.open_popup_action
                    }).open();
                    dialog.on('write_completed', this, this.write_completed);
                    dialog.on('write_completed', this, () => dialog.destroy());
                } else {
                    var index = this.dataset.get_id_index(id);
                    this.dataset.index = index;
                    if (this.write_right) {
                        this.do_switch_view('form', null, {mode: "edit"});
                    } else {
                        this.do_switch_view('form', null, {mode: "view"});
                    }
                }
                return false;
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
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);

                    id = item.evt[this.delegate_model_field][0]
                    this.dataset._model.call('delegate_write', [[id], {
                        'delegate_field': this.delegate_model_field,
                        'delegate_id': id,
                        'field_used': this.fields_used,
                        'delegate_relation': field_def.relation,
                        'delegate_data': data,
                    }]).then(result => {
                        if (!result || !Array.isArray(result) || !result.length) return callback(null);

                        this.visData.remove(result);
                        return this._internal_do_search(
                            [...this.last_domains, [this.delegate_model_field, '=', id]],
                            this.last_contexts,
                            this.last_group_bys,
                            true
                        )
                    });
                } else {
                    var id = item.evt.id;
                    this.dataset.write(id, data);
                }
            },

            on_remove: function (item, callback) {
                var self = this;

                function do_it() {
                    return $.when(self.dataset.unlink([item.evt.id])).then(function () {
                        callback(item);
                    });
                }

                if (this.options.confirm_on_delete) {
                    if (confirm(_t("Are you sure you want to delete this record ?"))) {
                        return do_it();
                    }
                } else
                    return do_it();
            },

            on_click: function (e) {
                // handle a click on a group header
                if (e.what == 'group-label') {
                    return this.on_group_click(e);
                }
            },

            on_group_click: function (e) {
                if (e.group == -1) {
                    return;
                }
                return this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: this.fields[this.last_group_bys[0]].relation,
                    res_id: e.group,
                    target: 'new',
                    views: [[false, 'form']]
                });
            },
            scale_current_window: function (factor) {
                if (this.timeline) {
                    this.current_window = this.timeline.getWindow();
                    this.current_window.end = moment(this.current_window.start).add(factor, 'hours');
                    this.timeline.setWindow(this.current_window);
                }
            },
            on_today_clicked: function () {
                this.current_window = {
                    start: new moment(),
                    end: new moment().add(24, 'hours')
                };

                if (this.timeline) {
                    this.timeline.setWindow(this.current_window);
                }
            },

            on_scale_day_clicked: function () {
                this.scale_current_window(24);
            },

            on_scale_week_clicked: function () {
                this.scale_current_window(24 * 7);
            },

            on_scale_month_clicked: function () {
                this.scale_current_window(24 * 30);
            },

            on_scale_year_clicked: function () {
                this.scale_current_window(24 * 365);
            }
        })
    ;

    core.view_registry.add('timeline2', TimelineView);
    return TimelineView;
})
;
