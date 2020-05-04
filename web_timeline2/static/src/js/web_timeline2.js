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
                this.headerOrientation = attrs['headerOrientation']
                this.overlap_field = attrs['overlap_field']
                this.readonly_field = attrs['readonly_field']
                this.delegate_model_field = attrs['delegate_model_field']

                this.parse_colors(attrs.colors)

                this.stack = utils.toBoolElse(attrs.stack || '', true);
                this.stackSubgroups = utils.toBoolElse(attrs.stackSubgroups || '', true);
                this.date_start = attrs.date_start;
                this.date_stop = attrs.date_stop;
                this.date_delay = attrs.date_delay;
                this.no_period = this.date_start === this.date_stop;
                this.display_scale_button = utils.toBoolElse(attrs.scale_button || '', true);


                this.event_type = attrs.field_event_type; //The field used to determine the type of the timeline event

                this.color_field = attrs.color_field;
                this.update_group = utils.toBoolElse(attrs.update_group || '', true);
                this.update_time = utils.toBoolElse(attrs.update_time || '', true);
                this.create = utils.toBoolElse(attrs.create || '', true);
                this.unlink = utils.toBoolElse(attrs.unlink || '', true);
                this.editable = utils.toBoolElse(attrs.editable || '', true);
                this.swap_element = utils.toBoolElse(attrs.swap_enable || '', false);

                this.zoomKey = attrs.zoomKey || '';
                this.mode = attrs.mode || attrs.default_window || 'fit';
                this.snapTime = attrs.minute_snap ? Function('"use strict";return (' + attrs.minute_snap + ')')() : 0;
                this.min_zoom = attrs.min_zoom ? Function('"use strict";return (' + attrs.min_zoom + ')')() : null;
                this.max_zoom = attrs.max_zoom ? Function('"use strict";return (' + attrs.max_zoom + ')')() : null;
                this.axis = attrs.axis;
                if (attrs.drag_data) {
                    this.dragData = py.eval(attrs.drag_data);
                } else {
                    this.dragData = [];
                }
                this.current_drag_data = null;
                this.default_group_by = attrs.default_group_by;

                this.visibleFrameQweb = utils.toBoolElse(attrs.visibleFrameQweb || '', false);
                this.tooltipOnItemUpdateTimeFormat = utils.toBoolElse(attrs.visibleFrameQweb || '', true);

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
                if (this.display_scale_button) {
                    this.$(".oe_timeline_button_scale_day").click(() => this.scale_current_window('day'));
                    this.$(".oe_timeline_button_scale_week").click(() => this.scale_current_window('week'));
                    this.$(".oe_timeline_button_scale_month").click(() => this.scale_current_window('month'));
                    this.$(".oe_timeline_button_scale_year").click(() => this.scale_current_window('year'));
                } else {
                    this.$(".scale_button").addClass('o_hidden')
                }
                this.$('#swap_button').click(() => this.swap_action())

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
                        this.fields = fields;
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
                    stack: this.stack,
                    stackSubgroups: this.stackSubgroups,
                    moment: function (date) {
                        return vis.moment(date).utc();
                    },
                    // onDropObjectOnItem: this.on_drop_object
                };
                if (this.swap_element) {
                    options.multiselect = true;
                }
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
                        const hour = this.snapTime * 60 * 1000;
                        return new moment(Math.round(date / hour) * hour).toDate();
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
                    options.zoomMin = this.min_zoom * 60 * 1000;
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
                this.timeline.on('drop', this._on_drop.bind(this));
                this.timeline.on('select', this._on_select.bind(this));
                if (this.default_group_by) {
                    this._init_drap_and_drop(this.dragData.find(el => el.group_by === this.default_group_by))
                }

            },

            _init_drap_and_drop: function (drag_data) {
                const $drag_item = this.$('#timeline2_drag_item')
                if (!this.dragData || !drag_data) {
                    this.current_drag_data = null;
                    $drag_item.empty().addClass('o_hidden');
                    return false;
                }
                if (this.current_drag_data && this.current_drag_data.field === drag_data.field) {
                    return true;
                }

                const field_def = this.fields[drag_data.field]
                if (!field_def.relation) {
                    $drag_item.empty().addClass('o_hidden');
                    return false;
                }
                this.current_drag_data = drag_data;

                $drag_item.empty().removeClass('o_hidden');
                const fieldsToRead = ['display_name', ...this.current_drag_data.other_fields || []]
                if (this.current_drag_data.color_field) {
                    fieldsToRead.push(this.current_drag_data.color_field)
                }
                new Model(field_def.relation)
                    .query(fieldsToRead)
                    .filter(this.current_drag_data.domain || field_def.domain || [])
                    .context(this.dataset.get_context())
                    .limit(this.current_drag_data.limit || 80)
                    .all()
                    .then((records) => {

                        for (const record of records) {
                            const $div = $(document.createElement('div'))
                            $div.addClass("badge");
                            $div.css("background-color", record[this.current_drag_data.color_field]);
                            $div.text(record.display_name);
                            $div.attr('data-id', record.id);
                            $div.attr('draggable', true);
                            $div.on('dragstart', this.handleObjectItemDragStart.bind(this));
                            $drag_item.append($div);
                        }
                    });
                return true;

            },

            handleObjectItemDragStart: function (event) {
                const dragSrcEl = $(event.target);
                event.dataTransfer = event.originalEvent.dataTransfer;
                event.dataTransfer.effectAllowed = "move";
                const objectItem = {
                    id: dragSrcEl.attr('data-id'),
                    content: dragSrcEl.text(),
                    target: this.dragTarget,
                    comeFromDrag: true,
                    // target: "item",
                };
                objectItem[this.current_drag_data.field] = dragSrcEl.attr('data-id')
                console.log("handleObjectItemDragStart", event, objectItem);
                event.dataTransfer.setData("text", JSON.stringify(objectItem));
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
                    'content':  evt.display_name,
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
                    if (this.visibleFrameQweb && r.type !== 'background') {
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
                this.visData.clear();
                this.visGroups.clear();
                this.groups = {};
                this.visGroups.add({
                    id: -1,
                    content: "-"
                })

                this.last_domains = domains;
                this.last_contexts = contexts;
                // select the group by
                let n_group_bys = [this.default_group_by];
                if (group_bys.length) {
                    n_group_bys = group_bys;
                }
                // self.convert_data_to_timeline(res, ...it)
                this.last_group_by = _.first(n_group_bys);
                this._init_drap_and_drop(this.dragData.find(el => el.group_by === this.last_group_by))
                this.fields_used = this.get_fields_to_read(n_group_bys);
                return this._internal_do_search(this.last_domains, this.last_contexts, this.last_group_by, false);
            },

            _internal_do_search: function (domains, contexts, group_by, updating) {
                return this.dataset._model.query(this.fields_used)
                    .filter(domains)
                    .context({...contexts, group_by_no_leaf: true, "grouped_on": group_by})
                    .lazy(false)
                    .group_by([group_by])
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
                        })).then(this._all_record_done.bind(this))
                    });
            },

            _all_record_done: function () {
                //    Unused but can be override in sub view
            },

            reload: function () {
                var self = this;
                if (this.last_domains !== undefined) {
                    self.current_window = self.timeline.getWindow();
                    return this.do_search(this.last_domains, this.last_contexts, [this.last_group_by]);
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
                    content: label ? label : _t("Undefined"),
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

                events.filter(evt => evt[this.date_start]).forEach((evt) => {
                        const data = this.event_data_transform(evt)
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
                this.dataset.read_ids([id], Object.keys(this.fields)).done((records) => {
                    this.visData.add(self.event_data_transform(records[0]))
                });
            },

            _on_drop: function (event) {
                const dropData = JSON.parse(event.event.dataTransfer.getData("text"));
                console.log(event);
                console.log(dropData);
                switch (event.what) {
                    case "background":
                        const toCreate = {
                            start: event.snappedTime,
                            group: event.group,
                            end: moment(event.time).add(this.snapTime, 'minutes'),
                        };
                        const snap = this.timeline.itemSet.options.snap || null;
                        const scale = this.timeline.body.util.getScale();
                        const step = this.timeline.body.util.getStep();
                        if (this.current_drag_data.range_full) {
                            toCreate.start = snap(moment(event.time).startOf(this.current_drag_data.range_full).utc().toDate(), scale, step);
                            toCreate.end = snap(moment(event.time).endOf(this.current_drag_data.range_full).utc().toDate(), scale, step);
                        } else if (snap) {
                            const m_time = moment(event.time);
                            toCreate.end = snap(moment(m_time).add(this.snapTime, 'minutes'), scale, step);
                        }
                        toCreate[this.current_drag_data.field] = dropData[this.current_drag_data.field]
                        this.on_add(toCreate, (item) => {
                        })
                        break;
                    case "item":
                        const to_write = {};
                        to_write[this.current_drag_data.field] = dropData[this.current_drag_data.field];
                        const item = this.visData.get(event.item);
                        if (this.delegate_model_field) {
                            const field_def = this.fields[this.delegate_model_field]
                            if (field_def.type !== 'many2one') return;
                            this._write_delegate(item.evt.id, to_write, field_def);
                        } else {
                            this._write(item.evt.id, to_write, {});
                        }
                        break;
                    default:
                        console.log("default", event);
                }
            },

            on_add: function (item, callback) {
                console.log("on_add", item);
                if (item.comeFromDrag) {
                    console.log("on add from drag and drop", item);
                    return callback(null);
                }
                var context = this.dataset.get_context();
                // Initialize default values for creation
                var default_context = {};
                default_context['default_'.concat(this.date_start)] = item.start;

                if (this.date_delay) {
                    default_context['default_'.concat(this.date_delay)] = 1;
                }
                if (this.date_stop) {
                    let stop = item.end;
                    if (!stop) {
                        stop = moment(item.start).add(this.snapTime, 'minutes').toDate();
                    }
                    default_context['default_'.concat(this.date_stop)] = stop;
                }
                if (item.group > 0) {
                    default_context['default_'.concat(this.last_group_by)] = item.group;
                }
                if (this.current_drag_data && item[this.current_drag_data.field]) {
                    default_context['default_'.concat(this.current_drag_data.field)] = parseInt(item[this.current_drag_data.field]);
                }
                context.add(default_context);
                // Show popup
                const dialogOption = {
                    res_model: this.dataset.model,
                    res_id: null,
                    context: context,
                    view_id: parseInt(this.open_popup_action)
                }
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);

                    dialogOption.res_model = field_def.relation;
                    dialogOption.create_function = function (data, options) {
                        return this._delegate_create(data, options).fail(error => callback(null));
                    }.bind(this);
                } else {
                    dialogOption.create_function = function (data, options) {
                        return this._create(data, options).fail(error => callback(null));
                    }.bind(this);
                }
                const dialog = new form_common.FormViewDialog(this, dialogOption)
                dialog.on('create_completed', this, () => {
                    callback(null);
                    dialog.destroy();
                });
                dialog.open();
                return false;
            },

            _create: function (data, options) {
                return this.dataset.create(data, options)
                    .then(result => {
                        return this._internal_do_search(
                            [['id', '=', result]],
                            this.last_contexts,
                            this.last_group_by,
                            true
                        )
                    })
            },
            _delegate_create: function (data, options) {
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
                        [...this.last_domains, [this.delegate_model_field, 'in', result]],
                        this.last_contexts,
                        this.last_group_by,
                        true
                    )
                })
            },

            on_update: function (item, callback) {
                console.log("on update from drag and drop", item);
                if (!this.delegate_model_field && !this.open_popup_action) {
                    this.dataset.index = this.dataset.get_id_index(item.evt.id);
                    if (this.write_right) {
                        this.do_switch_view('form', null, {mode: "edit"});
                    } else {
                        this.do_switch_view('form', null, {mode: "view"});
                    }
                }
                const dialogOption = {
                    res_model: this.dataset.model,
                    title: item.content,
                    res_id: item.evt.id,
                    context: this.dataset.get_context(),
                    view_id: parseInt(this.open_popup_action),
                }
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);

                    dialogOption.res_model = field_def.relation
                    dialogOption.res_id = item.evt[this.delegate_model_field][0]
                    dialogOption.title = item.evt[this.delegate_model_field][1]

                    dialogOption.write_function = function (ids, data, options) {
                        return this._write_delegate(ids, data, field_def).fail(error => callback(null));
                    }.bind(this);
                } else {
                    dialogOption.write_function = function (id, data, options) {
                        return this._write(id, data, options).fail(error => callback(null));
                    }.bind(this);
                }
                const dialog = new form_common.FormViewDialog(this, dialogOption)
                dialog.on('write_completed', this, () => dialog.destroy());
                dialog.open();
                return false;
            },

            _write: function (id, data, options = {}, auto_reload = true) {
                const defered = this.dataset.write(id, data, options)
                if (auto_reload) {
                    defered.then(result => {
                        return this._internal_do_search(
                            [['id', '=', id]],
                            this.last_contexts,
                            this.last_group_by,
                            true
                        )
                    })
                }
                return defered;
            },
            _write_delegate: function (ids, data, field_def, auto_reload = true) {
                const defered = this.dataset._model.call('delegate_write', [
                    [item.evt.id],
                    {
                        'delegate_field': this.delegate_model_field,
                        'delegate_ids': ids,
                        'field_used': this.fields_used,
                        'delegate_relation': field_def.relation,
                        'delegate_data': data,
                    }
                ])
                if (auto_reload) {
                    defered.then(result => {
                        if (!result || !Array.isArray(result) || !result.length) return callback(null);
                        this.visData.remove(result);
                        return this._internal_do_search(
                            [...this.last_domains, [this.delegate_model_field, '=', id]],
                            this.last_contexts,
                            this.last_group_by,
                            true
                        )
                    })
                }
                return defered;
            },

            on_move: function (item, callback) {
                var self = this;
                var event_start = item.start;
                var event_end = item.end;
                var data = {};
                if (item.group != -1) {
                    data[self.last_group_by] = item.group;
                }
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
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);
                    this._write_delegate(item.evt[this.delegate_model_field][0], data, field_def);
                } else {
                    this._write(item.evt.id, data)
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
                console.log(e, e.what);
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
                    res_model: this.fields[this.last_group_by].relation,
                    res_id: e.group,
                    target: 'new',
                    views: [[false, 'form']]
                });
            },

            on_today_clicked: function () {
                this.current_window = {
                    start: new moment(),
                    end: new moment().add(24, 'hours')
                };
                if (!this.display_scale_button && this.mode !== 'fit') {
                    this.current_window.start = new moment().startOf(this.mode);
                    this.current_window.end = moment().endOf(this.mode);
                }

                if (this.timeline) {
                    this.timeline.setWindow(this.current_window);
                }
            },

            on_scale_day_clicked: function () {
                this.scale_current_window('day');
            },

            on_scale_week_clicked: function () {
                this.scale_current_window('week');
            },

            on_scale_month_clicked: function () {
                this.scale_current_window('month');
            },

            on_scale_year_clicked: function () {
                this.scale_current_window('year');
            },

            scale_current_window: function (factor) {
                if (this.timeline) {
                    this.current_window = this.timeline.getWindow();
                    this.current_window.end = moment(this.current_window.start).add(1, factor);
                    this.timeline.setWindow(this.current_window);
                }
            },

            _on_select: function (evt) {
                console.log(evt, evt.items.length === 2);
                this.$('#swap_button').toggleClass('o_hidden', evt.items.length !== 2)
            },

            _swap_write_data: function (group_by_field_def, source, target) {
                let data = {
                    [this.last_group_by]: target.evt[this.last_group_by],
                    [this.date_start]: target.evt[this.date_start],
                    [this.date_stop]: target.evt[this.date_stop],
                }
                if (group_by_field_def.type === 'many2one' && Array.isArray(target.evt[this.last_group_by])) {
                    data[this.last_group_by] = target.evt[this.last_group_by][0]
                }
                return data;
            },
            swap_action: function () {
                const selected = this.timeline.getSelection()
                if (selected.length !== 2) {
                    return false;
                }
                const [el1, el2] = this.visData.get(selected);
                const field_def = this.fields[this.last_group_by];
                this._write(el1.evt.id, this._swap_write_data(field_def, el1, el2), {}, false);
                this._write(el2.evt.id, this._swap_write_data(field_def, el2, el1), {}, false);
                this._internal_do_search([['id', 'in', [el1.evt.id, el2.evt.id]]], this.last_contexts, this.last_group_by, true)
            }
        })
    ;

    core.view_registry.add('timeline2', TimelineView);
    return TimelineView;
})
;
