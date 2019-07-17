odoo.define('web_organization_chart.OrganizationChartModel', function (require) {
    "use strict";

    var AbstractModel = require('web.AbstractModel');

    var OrganizationChartModel = AbstractModel.extend({

        /**
         * @constructor
         */
        init: function () {
            this._super.apply(this, arguments);
        },

        /**
         * @override
         */
        load: function (params) {
            var self = this;
            this.modelName = params.modelName;
            this.fieldNames = params.fieldNames;
            if (!this.preload_def) {
                this.preload_def = $.Deferred();
                $.when(
                    this._rpc({model: this.modelName, method: 'check_access_rights', args: ["write", false]}),
                    this._rpc({model: this.modelName, method: 'check_access_rights', args: ["unlink", false]}),
                    this._rpc({model: this.modelName, method: 'check_access_rights', args: ["create", false]}))
                .then(function (write, unlink, create) {
                    self.write_right = write;
                    self.unlink_right = unlink;
                    self.create_right = create;
                    self.preload_def.resolve();
                });
            }

            this.data = {
                domain: params.domain,
                context: params.context,
            };

            return this.preload_def.then(this._loadOrganizationChart.bind(this));
        },

        /**
         * Read the records for the organization_chart.
         *
         * @private
         * @returns {jQuery.Deferred}
         */
        _loadOrganizationChart: function () {
            var self = this;
            return self._rpc({
                model: self.modelName,
                method: 'search_read',
                context: self.data.context,
                fields: self.fieldNames,
                domain: self.data.domain,
            })
            .then(function (events) {
                self.data.data = events;
                self.data.rights = {
                    'unlink': self.unlink_right,
                    'create': self.create_right,
                    'write': self.write_right,
                };
            });
        },
    });

    return OrganizationChartModel;
});
