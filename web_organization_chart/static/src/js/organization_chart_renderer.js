var nodeTemplate = function (data) {
    data.function = data.function || '';
    data.email = data.email ? data.email + '<br/>' :  '';
    return `<div class="${data.company_type}"><div class="title">${data.display_name}</div>
        <div class="content">${data.function}${data.email}</div></div>`;
};

odoo.define('web_organization_chart.OrganizationChartRenderer', function (require) {
    "use strict";

    var AbstractRenderer = require('web.AbstractRenderer');
    var utils = require('web.utils');
    var session = require('web.session');
    var QWeb = require('web.QWeb');

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

            var ajaxURLs = {
                'parent': function (nodeData) {
                    return 'get_parent_node?node_id=' + nodeData.id;
                },
                'children': function (nodeData) {
                    return 'get_children_nodes?node_id=' + nodeData.id;
                }
            };

            this.organization_chart = self.$organization_chart.empty().orgchart({
                'data': {},
                'ajaxURL': ajaxURLs,
                'nodeTemplate': nodeTemplate,
                'initCompleted': function ($chart) {
                    $('.node > .company').unbind('click');
                    $('.node > .company').on('click', function (event) {
                        event.id = $(this).parent().attr('id')
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
            // Compatible avec un seul noeud racine (avec une racine artificielle, on ne peut pas remonter l'arbre)
            var nodesData = null;

            data.forEach(function (item) {
                if (item.parent_id === false || data.map(x => x.id).indexOf(parseInt(item.parent_id[0])) === -1) {
                    nodesData = self.get_children(item, data);
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
                'relationship': parent.relationship,
                'display_name': parent.display_name,
                'function': parent.function,
                'email': parent.email,
                'company_type': parent.company_type,
                'children': [],
            };

            data.forEach(function (item) {
                if (item.parent_id && item.parent_id[0] === parent.id) {
                    nodesData.children.push(self.get_children(item, data));
                }
            });

            return nodesData;
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
