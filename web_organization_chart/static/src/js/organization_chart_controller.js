odoo.define('web_organization_chart.OrganizationChartController', function (require) {
    "use strict";

    var AbstractController = require('web.AbstractController');
    var dialogs = require('web.view_dialogs');
    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var _t = core._t;

    var OrganizationChartController = AbstractController.extend({
        custom_events: _.extend({}, AbstractController.prototype.custom_events, {
            onUpdate: '_onUpdate',
        }),

        /**
         * @constructor
         * @override
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.context = params.actionContext;
        },

        /**
         * @override
         */
        update: function (params, options) {
            this._super.apply(this, arguments);
            if (_.isEmpty(params)){
                return;
            }

            var self = this;
            var domains = params.domain;
            this.last_domains = domains;
            this.renderer.last_domains = domains;

            var fields = this.renderer.fieldNames;
            self._rpc({
                model: self.model.modelName,
                method: 'search_read',
                kwargs: {
                    fields: fields,
                    domain: domains,
                },
                context: self.getSession().user_context,
            }).then(function(data) {
                return self.renderer.on_data_loaded(data);
            });
        },

        /**
         * Opens a form view of a clicked organization_chart item (triggered by the OrganizationChartRenderer).
         *
         * @private
         */
        _onUpdate: function (event) {
            this.renderer = event.data.renderer;
            var id = event.data.item.id;

            this.do_action({
                type: 'ir.actions.act_window',
                res_model: this.model.modelName,
                res_id: parseInt(id, 10).toString() === id ? parseInt(id, 10) : id,
                views: [[false, 'form']],
                target: 'current',
                context: this.getSession().user_context,
            });
        },

    });

    return OrganizationChartController;
});
