odoo.define('web_action_top_button.Sidebar', function (require) {
    "use strict";

    var Sidebar = require("web.Sidebar");
    var Session = require("web.session");
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
            this.groups_top_button = false;
            this.sections.push({'name': 'buttons', 'label': _t('Buttons')});
            this.items['buttons'] = this.items['buttons'] || [];

            Session.user_has_group(
                'web_action_top_button.group_allow_action_top_button')
                .then(function (has_group) { self.groups_top_button = has_group });

            _.each(['print', 'action', 'relate'], function (type) {
                if (type in toolbarActions) {
                    var actions = toolbarActions[type];
                    if (actions && actions.length) {
                        for (var i = 0; i < actions.length; i++) {
                            if(actions[i].display_name.includes('Exporter') || actions[i].display_name.includes('Export')) {
                                actions.splice(i);
                            }
                        }

                        var items = _.map(actions, function (action) {
                            let response = {
                                label: action.name,
                                action: action,
                            }
                            if (self.groups_top_button) {
                                response.classname = 'btn btn-primary btn-sm o_sidebar_buttons o_sidebar_btn text-light';
                            }
                            return response;
                        });

                        if (self.groups_top_button) {
                            if(items.length > 0) { self._addItems('buttons', items); }
                        } else {
                            if(items.length > 0) { self._addItems(type === 'print' ? 'print' : 'other', items); }
                        }
                    }
                }
            });

            if ('other' in toolbarActions && !self.groups_top_button) {
                if(toolbarActions.other.length > 0) { this._addItems('other', toolbarActions.other); }
            }
        }
    });
});