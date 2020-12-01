odoo.define('groupby_expand.groupby_expand', function (require) {

    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var _t = core._t;

    ListRenderer.include({

        init: function (parent, state, params) {
            this.expand = (state.groupedBy.length && state.context['auto_expand_groupby']);
            var res = this._super.apply(this, arguments);
            return res;
        },

        render_auto_groups: function () {
            var self = this;
            _.each(self.state.data, function (group) {
                if (group) {
                    self.trigger_up('toggle_group', {group: group});
                }
            })
        },

        _renderGroupRow: function (group, groupLevel) {
            var aggregateValues = _.mapObject(group.aggregateValues, function (value) {
                return {value: value};
            });
            var $cells = this._renderAggregateCells(aggregateValues);
            if (this.hasSelectors) {
                $cells.unshift($('<td>'));
            }
            var name = group.value === undefined ? _t('Undefined') : group.value;
            var groupBy = this.state.groupedBy[groupLevel];
            if (group.fields[groupBy.split(':')[0]].type !== 'boolean') {
                name = name || _t('Undefined');
            }
            var $th = $('<th>')
                .addClass('o_group_name')
                .text(name + ' (' + group.count + ')');
            var $arrow = $('<span>')
                .css('padding-left', (groupLevel * 20) + 'px')
                .css('padding-right', '5px')
                .addClass('fa');
            if (group.count > 0) {
                $arrow.toggleClass('fa-caret-right', !group.isOpen)
                    .toggleClass('fa-caret-down', group.isOpen);
            }
            $th.prepend($arrow);
            if (group.isOpen && !group.groupedBy.length && (group.count > group.data.length)) {
                var $pager = this._renderGroupPager(group);
                var $lastCell = $cells[$cells.length - 1];
                $lastCell.addClass('o_group_pager').append($pager);
            }

            if (this.expand) {
                if (!group.isOpen) {
                    this.trigger_up('toggle_group', {group: group});
                }
            }

            return $('<tr>')
                .addClass('o_group_header')
                .toggleClass('o_group_open', group.isOpen)
                .toggleClass('o_group_has_content', group.count > 0)
                .data('group', group)
                .append($th)
                .append($cells);
        },

        _renderView: function () {
            var self = this;
            var is_grouped = !!this.state.groupedBy.length;

            if (self.expand) {
                $('button#expand_icon.list-expand').switchClass('list-expand', 'list-compress');
            } else {
                $('button#expand_icon.list-compress').switchClass('list-compress', 'list-expand');
            }

            if (is_grouped) {
                $('.o_main_content').addClass('groupby-list');

                $('button#expand_icon.list-expand').unbind('click').bind('click', function () {
                    self.expand = true;
                    self.render_auto_groups();
                    $(this).switchClass('list-expand', 'list-compress');
                });
                $('button#expand_icon.list-compress').unbind('click').bind('click', function () {
                    self.expand = false;
                    self.render_auto_groups();
                    $(this).switchClass('list-compress', 'list-expand');
                });
            } else {
                $('.o_main_content').removeClass('groupby-list');
            }
            return this._super();
        },

        _onRowClicked: function (event) {
            this.expand = false;
            return this._super(event)
        },
    });

});
