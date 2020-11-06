odoo.define('web_action_top_button.Sidebar', function (require) {
    "use strict";

    var Sidebar = require("web.Sidebar");
    var core = require('web.core');
    var _t = core._t;

    Sidebar.include({

        init: function (parent, options) {
            this._super.apply(this, arguments);
        },

        start: function () {
            var self = this;
            this._super.apply(this, arguments);
            this.$el.addClass('btn-group');
            this._redraw();
            this.$el.on('click', '.o_sidebar_btn', function (event) {
                var section = $(this).data('section');
                var index = $(this).data('index');
                var item = self.items[section][index];
                if (item.callback) {
                    item.callback.apply(self, [item]);
                } else if (item.action) {
                    self._onItemActionClicked(item);
                } else if (item.url) {
                    return true;
                }
                event.preventDefault();
            });
        },

        _addToolbarActions: function (toolbarActions) {
            var self = this;
            var top_items = [];
            this.sections.push({'name': 'buttons', 'label': _t('Buttons')});
            this.items['buttons'] = this.items['buttons'] || [];

            _.each(['print', 'action', 'relate'], function (type) {
                var items = toolbarActions[type];
                var out_items = [];
                if (items) {
                    for (var i = 0; i < items.length; i++) {
                        var action = items[i];
                        if (action.position === "top_button") {
                            top_items.push({
                                label: action.name,
                                action: action,
                                classname: 'btn btn-primary btn-sm o_sidebar_buttons o_sidebar_btn text-light'
                            });
                        }
                        else {
                            if((action.position === false) || (action.position && action.position !== "none") || (action.position === undefined)) {
                                out_items.push({
                                    label: action.name,
                                    action: action,
                                });
                            }
                        }
                    }
                    self._addItems(type === 'print' ? 'print' : 'other', out_items);
                }
            });
            self._addItems('buttons', top_items);

            if ('other' in toolbarActions) {
                this._addItems('other', toolbarActions.other);
            }
        }
    });
});