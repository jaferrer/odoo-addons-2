/* Odoo web_timeline
 * Copyright 2020 Ndp Systemes
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

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
    const formats = require('web.formats');
    var data_manager = require('web.data_manager');
    var Sidebar = require('web.Sidebar');

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
                this.elementType = [];
                this.visGroups = new vis.DataSet()
                this.visData = new vis.DataSet()
                this.current_search = {
                    domain: [],
                    groupBys: [],
                    context: {},
                    lastGroupBy: {},
                    view: {
                        groupBys: [],
                        domain: [],
                    }
                }
                this.subgroupStack = {
                    other: true,
                    background_unstacked: false,
                    range_unstacked: false,
                    box_unstacked: false,
                    point_unstacked: false,
                }
                this.searchDeferred = $.Deferred().resolve([]);
                this.ViewManager.on('switch_mode', this, (n_mode) => {
                    if (n_mode === "timeline2") {
                        this.timeline.redraw()
                    }
                });
                this._parse_attrs(this.fields_view.arch.attrs);
                return result
            },

            _parse_attrs: function (attrs) {
                if (!attrs.date_start) {
                    throw new Error(_t("Timeline view has not defined 'date_start' attribute."));
                }
                this.displayNumberOnGroup = utils.toBoolElse(attrs.number_on_group || '', false);
                this.showCurrentTime = utils.toBoolElse(attrs.show_current_time || '', true);
                this.showMinorLabels = utils.toBoolElse(attrs.show_minor_labels || '', true);
                this.showMajorLabels = utils.toBoolElse(attrs.show_major_labels || '', true);
                this.showWeekScale = utils.toBoolElse(attrs.show_week_scale || '', false);
                this.horizontalScroll = utils.toBoolElse(attrs.horizontal_scroll || '', false);
                this.inUtc = utils.toBoolElse(attrs.use_utc || '', true);
                this.pager = utils.toBoolElse(attrs.pager || '', true);
                this.multiSelect = utils.toBoolElse(attrs.multi_select || '', false);
                this.showSideBar = utils.toBoolElse(attrs.show_sidebar || '', false);
                this.headerOrientation = attrs['headerOrientation']
                this.overlap_field = attrs['overlap_field']
                this.readonly_field = attrs['readonly_field']
                this.delegate_model_field = attrs['delegate_model_field']
                this.min_height = attrs['min_height'] || 300

                this.defaultColor = attrs.default_color_code; //Default value, same as colors="'#COLOR_CODE':True"
                this.parse_colors(attrs.colors) //or a python expression '#COLOR_CODE1': expr;'#COLOR_CODE2':expr2; ...
                this.color_field = attrs.color_field; //The field used to determine the color code of the timeline event

                this.defaultType = attrs.item_type; //Default value, same as colors="'DEFAULT_TYPE':True"
                this.event_type = attrs.field_event_type; //The field used to determine the type of the timeline event
                this.parse_element_type(attrs.item_types) //or a python expression 'range': expr;'point' expr2; ...

                this.stack = utils.toBoolElse(attrs.stack || '', true);
                this.stackSubgroups = utils.toBoolElse(attrs.stackSubgroups || '', true);
                this.date_start = attrs.date_start;
                this.date_stop = attrs.date_stop;
                this.date_delay = attrs.date_delay;
                this.no_period = this.date_start === this.date_stop;
                this.display_scale_button = utils.toBoolElse(attrs.scale_button || '', true);

                this.update_group = utils.toBoolElse(attrs.update_group || '', true);
                this.update_time = utils.toBoolElse(attrs.update_time || '', true);
                this.create = utils.toBoolElse(attrs.create || '', true);
                this.unlink = utils.toBoolElse(attrs.unlink || '', true);
                this.editable = utils.toBoolElse(attrs.editable || '', true);
                this.swapEnable = utils.toBoolElse(attrs.swap_enable || '', false);
                this.disableClickOnGroup = utils.toBoolElse(attrs.disable_click_on_group || '', false);

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
                this.current_search.view.groupBys = attrs.default_group_by.split(',');
                this.current_search.groupBys = attrs.default_group_by.split(',');

                this.visibleFrameQweb = utils.toBoolElse(attrs.visibleFrameQweb || '', false);
                this.tooltipOnItemUpdateTimeFormat = utils.toBoolElse(attrs.visibleFrameQweb || '', true);

                if (!isNullOrUndef(attrs.quick_create_instance)) {
                    this.quick_create_instance = 'instance.' + attrs.quick_create_instance;
                }

                // If this field is set ot true, we don't open the event in form
                // view, but in a popup with the view_id passed by this parameter
                if (isNullOrUndef(attrs.event_open_popup) || !utils.toBoolElse(attrs.event_open_popup, true)) {
                    this.open_popup_action = false;
                } else {
                    this.open_popup_action = attrs.event_open_popup;
                }

            },

            render_sidebar: function ($node) {
                console.log(this.sidebar, this.options.sidebar, this.showSideBar)
                if (this.showSideBar && !this.sidebar && this.options.sidebar) {
                    this.sidebar = new Sidebar(this, {editable: this.is_action_enabled('edit')});
                    if (this.fields_view.toolbar) {
                        this.sidebar.add_toolbar(this.fields_view.toolbar);
                    }
                    var canDuplicate = this.is_action_enabled('create') && this.is_action_enabled('duplicate');
                    this.sidebar.add_items('other', _.compact([
                        this.is_action_enabled('delete') && {label: _t('Delete'), callback: this.on_button_delete},
                        canDuplicate && {label: _t('Duplicate'), callback: this.on_button_duplicate}
                    ]));
                    this.sidebar.appendTo($node);
                    this.sidebar.do_hide();
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
            parse_element_type: function (element_type) {
                if (element_type) {
                    this.elementType = _(element_type.split(';')).chain()
                        .compact()
                        .map(color_pair => {
                            const pair = color_pair.split(':');
                            const color = pair[0];
                            const expr = pair[1];
                            return [color, py.parse(py.tokenize(expr)), expr];
                        }).value();
                }
            },

            start: function () {
                const attrs = this.fields_view.arch.attrs;
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
                if (this.pager) {
                    this.$(".pager").removeClass('o_hidden')
                    this.$(".timeline2_pager_previous").click(() => this.page_previous())
                    this.$(".timeline2_pager_next").click(() => this.page_next())
                }
                this.$('#swap_button').click(() => this.swap_action())

                this.current_window = {
                    start: new moment(),
                    end: new moment().add(24, 'hours')
                };

                this.$el.addClass(attrs['class']);
                this._super();
                return data_manager.load_fields(this.dataset)
                    .then((fields) => {
                        this.fields = fields;
                        this.perm_model = this.dataset.model
                        if (this.delegate_model_field) {
                            const field_def = this.fields[this.delegate_model_field]
                            if (field_def.type !== 'many2one') throw Error('The delegate must be a Many2one not a ' + field_def.type);
                            this.perm_model = field_def.relation
                        }
                        return $.when(
                            this.get_perm('unlink'),
                            this.get_perm('write'),
                            this.get_perm('create')
                        ).then(() => {
                            this.init_timeline();
                            $(window).trigger('resize');
                        })

                    });
            },


            destroy: function () {
                return this._super.apply(this, arguments);
            },

            _get_option_timeline: function () {
                let options = {
                    groupOrder: this.group_order,
                    selectable: true,
                    minHeight: this.min_height,
                    showCurrentTime: this.showCurrentTime,
                    showMinorLabels: this.showMinorLabels,
                    showMajorLabels: this.showMajorLabels,
                    orientation: this.headerOrientation || 'both',
                    onAdd: this.on_add,
                    onMove: this.on_move,
                    onUpdate: this.on_update,
                    onRemove: this.on_remove,
                    zoomKey: this.zoomKey,
                    stack: this.stack,
                    stackSubgroups: this.stackSubgroups,
                    showWeekScale: this.showWeekScale,
                    verticalScroll: true,

                };
                if(this.inUtc){
                    options.moment = function (date) {
                        return vis.moment(date).utc();
                    }
                }
                if (this.swapEnable || this.multiSelect) {
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
                        if (!item) {
                            return '';
                        }
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
            on_attach_callback: function () {
                this._compute_height()
            },
            on_data_loaded: function (result) {
                this._compute_height()
            },
            _compute_height: function () {
                let height = this.$el.parent().height();
                height -= this.$el.find('.oe_timeline2_buttons').height();
                height -= this.$el.find('#timeline2_drag_item').height()
                height -= 10
                if (height > this.min_height) {
                    this.timeline.setOptions({
                        height: height + "px"
                    });
                }
            },

            init_timeline: function () {
                this.timeline = new vis.Timeline(this.$timeline.empty().get(0));
                const options = this._get_option_timeline()
                this.timeline.setOptions(options);
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
                            $div.addClass("badge timeline2_draggable");
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
                for (const [color, expr] of this.colors) {
                    if (py.PY_isTrue(py.evaluate(expr, context))) {
                        return type;
                    }
                }
                return this.defaultColor;
            },
            _get_type_for_item(evt) {
                if (this.event_type && evt.hasOwnProperty(this.event_type)) {
                    return evt[this.event_type];
                }
                const context = _.extend({}, evt, {
                    uid: session.uid,
                    current_date: moment().format('YYYY-MM-DD')
                });
                for (const [type, expr] of this.elementType) {
                    if (py.PY_isTrue(py.evaluate(expr, context))) {
                        return type;
                    }
                }
                return this.defaultType
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
                const type = this._get_type_for_item(evt);
                var r = {
                    'start': date_start,
                    'content': evt.display_name,
                    'title': evt.display_name,
                    'id': evt.id,
                    'type': type,
                    'evt': evt,
                    'style': 'background-color: ' + color + ';'
                };

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
                if (!Array.isArray(n_group_bys)) {
                    n_group_bys = [n_group_bys]
                }

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
                return this.searchDeferred.then(() => {
                    this.current_search.domain = domains;
                    this.current_search.context = contexts;
                    this.current_search.context = contexts;
                    // select the group by
                    this.current_search.groupBys = this.current_search.view.groupBys;
                    if (group_bys.length) {
                        this.current_search.groupBys = group_bys;
                    }
                    // self.convert_data_to_timeline(res, ...it)
                    this.current_search.lastGroupBy = _.last(this.current_search.groupBys);
                    this._init_drap_and_drop(this.dragData.find(el => el.group_by === this.current_search.lastGroupBy));
                    this.searchDeferred = this._load_all_data().done((...res) => this.on_data_loaded(res));
                    return this.searchDeferred;
                });
            },

            reload: function () {
                if (this.current_search.domain !== undefined) {
                    this.current_window = this.timeline.getWindow();
                    return this.do_search(this.current_search.domain, this.current_search.context, this.current_search.groupBys);
                }
            },

            _load_all_data: function () {
                this.visData.clear();
                if (this.current_search.groupBys) {
                    return this._load_all_data_with_group();
                }
                return this._load_all_data_without_group()
            },
            _load_all_data_without_group: function () {
                return this._internal_do_search(this.current_search.domain, this.current_search.context)
            },
            _load_all_data_with_group: function () {
                return this.dataset._model
                    .query(this.get_fields_to_read(this.current_search.groupBys))
                    .filter(this.current_search.domain)
                    .context({
                        ...this.current_search.context,
                        grouped_on: this.current_search.lastGroupBy,
                        group_by_no_leaf: true
                    }).lazy(false).group_by(this.current_search.groupBys).then(result => {
                        this.visGroups.clear();
                        this.visGroups.add({
                            id: -1,
                            content: "-"
                        })
                        return $.when.apply($,
                            result.flatMap(grouping => {
                                this._populate_vis_group(grouping);
                                return this._internal_do_search(grouping.model.domain(), grouping.model.context().eval())
                            })
                        )
                    });
            },

            _internal_do_search: function (domains = this.current_search.domain, contexts = this.current_search.context) {
                const fields_used = this.get_fields_to_read(this.current_search.groupBys);
                return this.dataset._model.query(fields_used)
                    .filter(domains)
                    .context({...contexts, "grouped_on": this.current_search.lastGroupBy})
                    .all()
                    .then(events => {
                        return events.filter(evt => evt[this.date_start]).map(evt => {
                            const el = this.convert_data_to_timeline(evt);
                            if (this.visData.get(el.id)) {
                                this.visData.update(el);
                            } else {
                                this.dataset.ids.push(el.id);
                                this.visData.add(el);
                            }
                            return el;
                        })
                    })
            },

            _populate_vis_group: function (grouping) {
                let grouped_ons = grouping.get('grouped_on')
                let values = grouping.get('value')
                if (!Array.isArray(grouped_ons)) {
                    grouped_ons = [grouped_ons];
                    values = [values];
                }
                let previous_grouped_on = null;
                for (const [idx, grouped_on] of grouped_ons.entries()) {
                    let value = values[idx];
                    let label = value;
                    if (Array.isArray(value)) {
                        label = value[1];
                        value = value[0];
                    }
                    let grp_id = grouped_on + '_' + value;
                    if (previous_grouped_on) {

                        grp_id = previous_grouped_on + "_" + grp_id;
                    }
                    label = label || "Sans " + this.fields[grouped_on].string;
                    if (!this.visGroups.get(grp_id)) {
                        let current_group = {
                            id: grp_id,
                            content: label || this.fields[grouped_on].string,
                            _id: value,
                            _name: label,
                            field: grouped_on,
                            treeLevel: idx,
                        }
                        if (idx === grouped_ons.length - 1) {
                            if (this.overlap_field) {
                                current_group['subgroupStack'] = this.subgroupStack;
                                current_group['subgroupOrder'] = function (a, b) {
                                    return a.subgroupOrder - b.subgroupOrder;
                                };
                            }
                            if (this.displayNumberOnGroup) {
                                current_group.content += " (" + grouping.get('length') + ")"
                            }
                        }
                        this.visGroups.add(current_group);
                    }
                    if (previous_grouped_on !== null) {
                        const previous_vis_group = this.visGroups.get(previous_grouped_on);
                        this.visGroups.update({
                            id: previous_grouped_on,
                            nestedGroups: [...previous_vis_group.nestedGroups || [], grp_id]
                        })
                    }
                    previous_grouped_on = grp_id;
                }
            },
            _get_id: function (value) {
                if (Array.isArray(value)) {
                    return value[0];
                }
                return value;
            },

            convert_data_to_timeline(evt) {
                const data = this.event_data_transform(evt)
                const data_type = (data.type || 'box')
                const suffix = evt[this.overlap_field] ? "stacked_" + data.id : "unstacked"
                const subgroup = data_type + "_" + suffix;

                const visEvt = {
                    ...data,
                };
                if (this.current_search.groupBys) {
                    visEvt.group = this.current_search.groupBys.map(grp => grp + '_' + this._get_id(evt[grp])).join("_")
                }
                if (data_type !== 'background' && this.overlap_field) {
                    visEvt["subgroup"] = subgroup;
                    visEvt["subgroupOrder"] = suffix.includes('stacked') ? 10 : 100;
                }
                return visEvt;
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
                        }, this.current_drag_data.create_auto)
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
                        console.debug("default", event);
                }
            },

            _get_default_values: function (group, item) {
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
                if (group) {
                    default_context['default_'.concat(group.field)] = group._id;
                }
                if (this.current_drag_data && item[this.current_drag_data.field]) {
                    default_context['default_'.concat(this.current_drag_data.field)] = parseInt(item[this.current_drag_data.field]);
                }
                return default_context;
            },

            on_add: function (item, callback, auto_create = false) {
                if (item.comeFromDrag) {
                    return callback(null);
                }
                var context = this.dataset.get_context();
                let group = null;
                if (item.group) {
                    group = this.visGroups.get(item.group)
                    if (group.field !== this.current_search.lastGroupBy) {
                        return callback(null);
                    }
                }
                // Initialize default values for creation
                var default_context = this._get_default_values(group, item);
                context.add(default_context);

                if (auto_create) {
                    if (this.delegate_model_field) {
                        console.debug('Auto create on delegate model is not supported')
                    } else {
                        return this.dataset.default_get(this.get_fields_to_read(this.current_search.groupBys), {
                            context: context
                        }).then(data => {
                            this._create(data).fail((error, event) => {
                                event.preventDefault();
                                this.on_add(item, callback, false);
                            });
                        })
                    }
                }
                // Show popup
                const dialogOption = {
                    res_model: this.dataset.model,
                    res_id: null,
                    context: context,
                    view_id: parseInt(this.open_popup_action),
                    disable_multiple_selection: true,
                }
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);
                    dialogOption.res_model = field_def.relation;
                    dialogOption.create_function = function (data, options) {
                        return this._create_delegate(data, field_def).fail(error => callback(null));
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
                dialog.on('on_button_cancel', this, () => {
                    dialog.destroy();
                    callback(null)
                })
                dialog.open();


                return false;
            },

            _create: function (data, options = {}) {
                return this.dataset.create(data, options)
                    .then(result => {
                        return this._internal_do_search(
                            [['id', '=', result]],
                            this.current_search.context
                        )
                    })
            },
            _create_delegate: function (data, field_def, auto_reload = true) {
                const deferred = this.dataset._model.call('delegate_create', [
                    {
                        'delegate_field': this.delegate_model_field,
                        'field_used': this.fields_used,
                        'delegate_relation': field_def.relation,
                        'delegate_data': data,
                    }
                ], {context: this.current_search.context})
                if (auto_reload) {
                    deferred.then(result => {
                        if (!result || !Array.isArray(result) || !result.length) return;
                        this.visData.remove(result);
                        return this._internal_do_search(
                            [...this.current_search.domain, ['id', 'in', result]],
                            this.current_search.context,
                        )
                    })
                }
                return deferred;
            },

            on_update: function (item, callback) {
                if (!this.delegate_model_field && !this.open_popup_action) {
                    this.dataset.select_id(item.evt.id);
                    if (this.permissions['write']) {
                        return this.do_switch_view('form', {mode: "edit"});
                    } else {
                        return this.do_switch_view('form', {mode: "view"});
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
                dialog.on('on_button_cancel', this, () => {
                    dialog.destroy();
                    callback(null)
                })
                dialog.open();
                return false;
            },

            _write: function (id, data, options = {}, auto_reload = true) {
                const defered = this.dataset.write(id, data, options)
                if (auto_reload) {
                    defered.then(result => {
                        return this._internal_do_search(
                            [...this.current_search.domain, ['id', '=', id]],
                            this.current_search.context,
                        )
                    })
                }
                return defered;
            },

            _write_delegate: function (id, data, field_def, auto_reload = true) {
                const defered = this.dataset._model.call('delegate_write', [
                    [id],
                    {
                        'delegate_field': this.delegate_model_field,
                        'delegate_id': id,
                        'field_used': this.fields_used,
                        'delegate_relation': field_def.relation,
                        'delegate_data': data,
                    }
                ])
                if (auto_reload) {
                    defered.then(result => {
                        if (!result || !Array.isArray(result) || !result.length) return;
                        this.visData.remove(result);
                        return this._internal_do_search(
                            [...this.current_search.domain, ['id', 'in', result]],
                            this.current_search.context,
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
                const group = this.visGroups.get(item.group)
                if (item.group !== -1) {
                    data[group.field] = group._id;
                    if (group.field !== this.current_search.lastGroupBy) {
                        return callback(null); //Moving element on group only allowed on final group
                    }
                } else {
                    if (this.fields[this.current_search.lastGroupBy].required) {
                        return callback(null);
                    }
                    data[this.current_search.lastGroupBy] = false;
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
                if (!item.evt) {
                    return callback(item);
                }
                if (this.options.confirm_on_delete) {
                    if (confirm(_t("Are you sure you want to delete this record ?"))) {
                        return this._unlink(item.evt).then(res => res ? callback(item) : callback(null));
                    }
                    return callback(null);
                }
                return this._unlink(item.evt).then(res => res ? callback(item) : callback(null));
            },

            _unlink: function (evt) {
                if (this.delegate_model_field) {
                    const field_def = this.fields[this.delegate_model_field]
                    if (field_def.type !== 'many2one') return callback(null);
                    return this.dataset._model.call('delegate_unlink', [
                        [evt.id],
                        {
                            'delegate_field': this.delegate_model_field,
                            'delegate_id': evt[this.delegate_model_field][0],
                            'delegate_relation': field_def.relation,
                        }
                    ]).then((result) => {
                        result.forEach(it => this.visData.remove(it))
                        return result.length > 0;
                    })
                }
                return self.dataset.unlink([evt.id]);
            },

            on_click: function (e) {
                // handle a click on a group header
                if (e.what == 'group-label') {
                    return this.on_group_click(e);
                }
            },

            on_group_click: function (e) {
                const grp = this.visGroups.get(e.group)
                if (grp.id == -1 || grp.field !== this.current_search.lastGroupBy || this.disableClickOnGroup) {
                    return;
                }
                return this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: this.fields[grp.field].relation,
                    res_id: grp._id,
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
                    this.mode = factor;
                    this.timeline.setWindow(this.current_window);
                }
            },

            page_previous: function () {
                if (this.timeline) {
                    const current_window = this.timeline.getWindow();
                    const start = new Date(current_window.start);
                    const end = new Date(current_window.end);
                    this.current_window.start = new Date(start.valueOf() - (end - start));
                    this.current_window.end = start;
                    this.timeline.setWindow(this.current_window);
                }
            },

            page_next: function () {
                if (this.timeline) {
                    const current_window = this.timeline.getWindow();
                    const start = new Date(current_window.start);
                    const end = new Date(current_window.end);
                    this.current_window.start = end;
                    this.current_window.end = new Date(end.valueOf() + (end - start));
                    this.timeline.setWindow(this.current_window);
                }
            },

            _on_select: function (evt) {
                if (this.swapEnable){
                    this.$('#swap_button').toggleClass('o_hidden', evt.items.length !== 2)
                }
                if (this.sidebar) {
                    console.log("On select", evt.items)
                    if (evt.items.length > 0) {
                        console.log('show')
                        this.sidebar.do_show();
                    } else {
                        console.log('hide')
                        this.sidebar.do_hide();
                    }

                }
            },

            get_selected_ids: function () {
                if(!this.timeline){
                    return [];
                }
                const selected = this.timeline.getSelection();
                if (selected.length <= 0) {
                    return [];
                }
                return this.visData.get(selected).map((el) => el.evt.id);
            },

            _swap_write_data: function (group_by_field_def, source, target) {
                let data = {
                    [this.current_search.lastGroupBy]: target.evt[this.current_search.lastGroupBy],
                    [this.date_start]: target.evt[this.date_start],
                    [this.date_stop]: target.evt[this.date_stop],
                }
                if (group_by_field_def.type === 'many2one' && Array.isArray(target.evt[this.current_search.lastGroupBy])) {
                    data[this.current_search.lastGroupBy] = target.evt[this.current_search.lastGroupBy][0]
                }
                return data;
            },
            swap_action: function () {
                const selected = this.timeline.getSelection()
                if (selected.length !== 2) {
                    return false;
                }
                const [el1, el2] = this.visData.get(selected);
                const field_def = this.fields[this.current_search.lastGroupBy];
                $.when(
                    this._write(el1.evt.id, this._swap_write_data(field_def, el1, el2), {}, false),
                    this._write(el2.evt.id, this._swap_write_data(field_def, el2, el1), {}, false)
                ).then(() => this._internal_do_search([['id', 'in', [el1.evt.id, el2.evt.id]]]))
            },
        })
    ;

    core.view_registry.add('timeline2', TimelineView);
    return TimelineView;
})
;
