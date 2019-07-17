var nodeTemplate = function (data) {
    return `<div class="title">${data.display_name}</div>
        <div class="content">${data.content}</div>`;
};

odoo.define('web_organization_chart.OrganizationChartRenderer', function (require) {
    "use strict";

    var AbstractRenderer = require('web.AbstractRenderer');
    var utils = require('web.utils');
    var session = require('web.session');
    var QWeb = require('web.QWeb');
    var field_utils = require('web.field_utils');

    var OrganizationChartRenderer = AbstractRenderer.extend({
        template: "OrganizationChartView",

        /**
         * @constructor
         */
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.modelName = params.model;
            this.mode = params.mode;
            this.options = params.options;
            this.permissions = params.permissions;
            this.colors = params.colors;
            this.fieldNames = params.fieldNames;
            this.view = params.view;
            this.modelClass = this.view.model;
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            // var attrs = this.arch.attrs;
            this.$organization_chart = this.$el;
            this._super.apply(this, self);
        },

        /**
         * @override
         */
        _render: function () {
            var self = this;
            return $.when().then(function () {
                // Prevent Double Rendering on Updates
                if (!self.organization_chart) {
                    self.init_organization_chart();
                    $(window).trigger('resize');
                }
            });
        },

        /**
         * Initializes the organization_chart.
         *
         * @private
         */
        init_organization_chart: function () {
            var self = this;

            this.qweb = new QWeb(session.debug, {_s: session.origin}, false);
            if (this.arch.children.length) {
                var tmpl = utils.json_node_to_xml(
                    _.filter(this.arch.children, function (item) {
                        return item.tag === 'templates';
                    })[0]
                );
                this.qweb.add_template(tmpl);
            }

            this.organization_chart = self.$organization_chart.empty().orgchart({
                'data': {},
                'nodeTemplate': nodeTemplate,
                'toggleSiblingsResp': true,
                'initCompleted': function ($chart) {
                    $('.node').unbind('click');
                    $('.node').on('click', function (event) {
                        event.id = $(this).attr('id')
                        self.on_update(event);
                    });
                }
            });

            this.on_data_loaded(this.modelClass.data.data);
        },

        /**
         * Load records.
         *
         * @private
         * @returns {jQuery.Deferred}
         */
        on_data_loaded: function (data) {
            var self = this;
            var nodesData = {
                'display_name': this.modelClass,
                'children': [],
            };

            data.forEach(function (item) {
                if (item.parent_id === false || data.map(x => x.id).indexOf(parseInt(item.parent_id[0])) === -1) {
                    nodesData.children.push(self.get_children(item, data));
                }
            });

            this.organization_chart.init({
                'data': nodesData,
            });
        },

        get_children: function (parent, data) {
            var self = this;
            var nodesData = {
                'id': parent.id,
                'display_name': parent.display_name,
                'content': this.render_chart_item(parent),
                'children': [],
            };

            data.forEach(function (item) {
                if (item.parent_id && item.parent_id[0] === parent.id) {
                    nodesData.children.push(self.get_children(item, data));
                }
            });

            return nodesData;
        },

        render_chart_item: function (evt) {
            if (this.qweb.has_template('chart-item')) {
                return this.qweb.render('chart-item', {
                    'record': evt,
                    'field_utils': field_utils
                });
            }

            console.error(
                _t('Template "chart-item" not present in timeline view definition.')
            );
        },

        /**
         * Trigger onUpdate.
         *
         * @private
         */
        on_update: function (item, callback) {
            this._trigger(item, callback, 'onUpdate');
        },

        /**
         * trigger_up encapsulation adds by default the rights, and the renderer.
         *
         * @private
         */
        _trigger: function (item, callback, trigger) {
            this.trigger_up(trigger, {
                'item': item,
                'callback': callback,
                'rights': this.modelClass.data.rights,
                'renderer': this,
            });
        },

    });

    return OrganizationChartRenderer;
});
