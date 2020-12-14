odoo.define('web_timeline.TimelineController', function (require) {
    "use strict";

    var AbstractController = require('web.AbstractController');
    var dialogs = require('web.view_dialogs');
    var core = require('web.core');
    var time = require('web.time');
    var Dialog = require('web.Dialog');

    var _t = core._t;

    var TimelineController = AbstractController.extend({
        custom_events: _.extend({}, AbstractController.prototype.custom_events, {
            onGroupClick: '_onGroupClick',
            onUpdate: '_onUpdate',
            onRemove: '_onRemove',
            onMove: '_onMove',
            onAdd: '_onAdd',
        }),

        /**
         * @constructor
         * @override
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.open_popup_action = params.open_popup_action;
            this.date_start = params.date_start;
            this.date_stop = params.date_stop;
            this.date_delay = params.date_delay;
            this.context = params.actionContext;
            this.moveQueue = [];
            this.debouncedInternalMove = _.debounce(this.internalMove, 0);
        },

        /**
         * @override
         */
        update: function (params, options={}) {
            this._super.apply(this, arguments);
            if (_.isEmpty(params)){
                return;
            }
            var domains = params.domain;
            var contexts = params.context;
            // select the group by
            if (params.groupBy.length === 0 && this.renderer.arch.attrs.default_group_by) {
                params.groupBy = this.renderer.arch.attrs.default_group_by.split(',');
            }
            const partial = options.partial_update !== undefined && options.partial_update
            if (!partial){
                this.renderer.last_group_bys = params.groupBy;
                this.renderer.lastGroupBy = _.last(params.groupBy);
                this.renderer.last_domains = domains;
            }
            this.searchDeferred = this.renderer._load_data(params, {}, !partial);
            return this.searchDeferred;
        },

        /**
         * Gets triggered when a group in the timeline is clicked (by the TimelineRenderer).
         *
         * @private
         * @returns {jQuery.Deferred}
         */
        _onGroupClick: function (event) {
            var groupField = this.renderer.last_group_bys[0];
            const grp = this.renderer.visGroups.get(event.group)
            if (!grp.id || grp.id == -1 || this.renderer.view.disableClickOnGroup) {
                return;
            }
            return this.do_action({
                type: 'ir.actions.act_window',
                res_model: this.renderer.view.fields[groupField].relation,
                res_id: event.data.item.group,
                target: 'new',
                views: [[false, 'form']]
            });
        },

        /**
         * Opens a form view of a clicked timeline item (triggered by the TimelineRenderer).
         *
         * @private
         */
        _onUpdate: function (event) {
            var self = this;
            this.renderer = event.data.renderer;
            var rights = event.data.rights;
            var item = event.data.item;
            var id = item.evt.id;
            id = parseInt(id, 10).toString() === id ? parseInt(id, 10) : id
            var title = item.evt.__name;
            if (this.open_popup_action) {
                new dialogs.FormViewDialog(this, {
                    res_model: this.model.modelName,
                    res_id: id,
                    context: this.getSession().user_context,
                    title: title,
                    view_id: Number(this.open_popup_action),
                    on_saved: function () {
                        self.write_completed([id]);
                    },
                }).open();
            } else {
                var mode = 'readonly';
                if (rights.write) {
                    mode = 'edit';
                }
                this.trigger_up('switch_view', {
                    view_type: 'form',
                    res_id: parseInt(id, 10).toString() === id ? parseInt(id, 10) : id,
                    mode: mode,
                    model: this.model.modelName,
                });
            }
        },

        /**
         * Gets triggered when a timeline item is moved (triggered by the TimelineRenderer).
         *
         * @private
         */
        _onMove: function (event) {
            var item = event.data.item;
            var view = this.renderer.view;
            var fields = view.fields;
            var event_start = item.start;
            var event_end = item.end;
            var data = {};
            const group = event.data.renderer.visGroups.get(item.group)
            const lastGroupBy = _.last(this.renderer.modelClass.last_params.groupBy)
            if (item.group !== -1) {
                if (group.field !== lastGroupBy) {
                    return event.data.callback(null); //Moving element on group only allowed on final group
                }
                data[group.field] = group._id;
            } else {
                if (fields[lastGroupBy].required) {
                    return event.data.callback(null);
                }
                data[lastGroupBy] = false;
            }
            // In case of a move event, the date_delay stay the same, only date_start and stop must be updated
            data[this.date_start] = time.auto_date_to_str(event_start, fields[this.date_start].type);
            if (this.date_stop) {
                // In case of instantaneous event, item.end is not defined
                if (event_end) {
                    data[this.date_stop] = time.auto_date_to_str(event_end, fields[this.date_stop].type);
                } else {
                    data[this.date_stop] = data[this.date_start];
                }
            }
            if (this.date_delay && event_end) {
                var diff_seconds = Math.round((event_end.getTime() - event_start.getTime()) / 1000);
                data[this.date_delay] = diff_seconds / 3600;
            }

            this.moveQueue.push({
                id: event.data.item.id,
                data: data,
                event: event
            });

            this.debouncedInternalMove();
        },

        /**
         * Write enqueued moves to Odoo. After all writes are finished it updates the view once
         * (prevents flickering of the view when multiple timeline items are moved at once).
         *
         * @returns {jQuery.Deferred}
         */
        internalMove: function () {
            var self = this;
            var queue = this.moveQueue.slice();
            this.moveQueue = [];
            var defers = [];
            _.each(queue, function(item) {
                defers.push(self._rpc({
                    model: self.model.modelName,
                    method: 'write',
                    args: [
                        [item.event.data.item.id],
                        item.data,
                    ],
                    context: self.getSession().user_context,
                }).then(function() {
                    item.event.data.callback(item.event.data.item);
                    return item.event.data.item.id
                }));
            });
            return $.when.apply($, defers).done(function(...ids) {
                self.write_completed(ids, {
                    adjust_window: false
                });
            });
        },

        /**
         * Triggered when a timeline item gets removed from the view.
         * Requires user confirmation before it gets actually deleted.
         *
         * @private
         * @returns {jQuery.Deferred}
         */
        _onRemove: function (e) {
            var self = this;

            function do_it(event) {
                return self._rpc({
                    model: self.model.modelName,
                    method: 'unlink',
                    args: [
                        [event.data.item.id],
                    ],
                    context: self.getSession().user_context,
                }).then(function () {
                    var unlink_index = false;
                    for (var i = 0; i < self.model.data.data.length; i++) {
                        if (self.model.data.data[i].id === event.data.item.id) {
                            unlink_index = i;
                        }
                    }
                    if (!isNaN(unlink_index)) {
                        self.model.data.data.splice(unlink_index, 1);
                    }

                    event.data.callback(event.data.item);
                });
            }

            var message = _t("Are you sure you want to delete this record?");
            var def = $.Deferred();
            Dialog.confirm(this, message, {
                title: _t("Warning"),
                confirm_callback: function() {
                    do_it(e)
                        .done(def.resolve.bind(def, true))
                        .fail(def.reject.bind(def));
                },
            });
            return def.promise();
        },

        /**
         * Triggered when a timeline item gets added and opens a form view.
         *
         * @private
         */
        _onAdd: function (event) {
            var self = this;
            var item = event.data.item;
            let group = this.renderer.visGroups.get(item.group);
            // Initialize default values for creation
            var default_context = {};
            default_context['default_'.concat(this.date_start)] = item.start;
            if (this.date_delay) {
                default_context['default_'.concat(this.date_delay)] = 1;
            }
            if (this.date_start) {
                default_context['default_'.concat(this.date_start)] = moment(item.start).add(1, 'hours').toDate();
            }
            if (group) {
                default_context['default_'.concat(group.field)] = group._id;
            }
            if (this.date_stop && item.end) {
                default_context['default_'.concat(this.date_stop)] = moment(item.end).add(1, 'hours').toDate();
            }
            // Show popup
            new dialogs.FormViewDialog(this, {
                res_model: this.model.modelName,
                res_id: null,
                context: _.extend(default_context, this.context),
                view_id: Number(this.open_popup_action),
                on_saved: function (record) {
                    self.create_completed([record.res_id]);
                },
            }).open().on('closed', this, function () {
                event.data.callback();
            });

            return false;
        },

        /**
         * Triggered upon completion of a new record.
         * Updates the timeline view with the new record.
         *
         * @returns {jQuery.Deferred}
         */
        create_completed: function (id) {
            var self = this;
            return this._rpc({
                model: this.model.modelName,
                method: 'read',
                args: [
                    id,
                    this.model.fieldNames,
                ],
                context: this.context,
            })
            .then(function (records) {
                var new_event = self.renderer.event_data_transform(records[0]);
                var items = self.renderer.timeline.itemsData;
                items.add(new_event);
                self.renderer.timeline.setItems(items);
                self.reload();
            });
        },

        /**
         * Triggered upon completion of writing a record.
         */
        write_completed: function (ids, options) {
            var params = {
                domain: [['id', 'in', ids]],
                context: this.context,
                groupBy: this.renderer.last_group_bys,
            };
            this.update(params, {...options, partial_update: true});
        },
    });

    return TimelineController;
});
