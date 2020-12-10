odoo.define('web_timeline.TimelineModel', function (require) {
    "use strict";

    var AbstractModel = require('web.AbstractModel');

    var TimelineModel = AbstractModel.extend({

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
            this.last_params = params || this.last_params
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
                    self.data.rights = {
                        'unlink': true,
                        'create': true,
                        'write': true,
                    };
                    self.preload_def.resolve();
                });
            }

            this.data = {
                domain: params.domain,
                context: params.context,
            };

            return this.preload_def;
        },

        reload: function (handle, params) {
            return this._super(handle, params)
        },

        _read_group: function (params) {
            if (!Array.isArray(params.groupBy)) {
                params.groupBy = [params.groupBy]
            }
            let def = $.Deferred()
            if(params.groupBy.length <= 0){
                def.resolve([])
            } else {
                def = this._rpc({
                    model: this.modelName,
                    method: 'read_group',
                    fields: params.fieldNames,
                    domain: params.domain,
                    context: {
                        ...params.context,
                        grouped_on: _.last(params.groupBy),
                        group_by_no_leaf: true
                    },
                    groupBy: params.groupBy,
                    orderBy: params.orderedBy,
                    lazy: true,
                })
            }
            return def;
        },
        _do_search: function (params) {
            const fields_used = params.fieldNames
            return this._rpc({
                model: this.modelName,
                method: 'search_read',
                kwargs: {
                    fields: fields_used,
                    domain: params.domain,
                },
                context: {...params.context, "grouped_on": _.last(params.groupBy)},
            })
        },
    });

    return TimelineModel;
});
