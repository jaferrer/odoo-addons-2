odoo.define('web_ui_pos_partner_point_of_sale.models', function (require) {
    "use strict";

    var rpc = require('web.rpc');
    var exports = require('point_of_sale.models');
    var _super_posmodel = exports.PosModel.prototype;

    exports.change_domain = function(model_name, domain, concat) {
        if (!(domain instanceof Array)) {
            domain = [domain];
        }
        var models = exports.PosModel.prototype.models;
        for (var i = 0; i < models.length; i++) {
            var model = models[i];
            if (model.model === model_name) {
                if (concat == true) {
                    model.domain = model.domain.concat(domain || []);
                } else {
                    model.domain = domain
                }
            }
        }
    };

    exports.PosModel = exports.PosModel.extend({
        initialize: function (session, attributes) {
            return _super_posmodel.initialize.call(this, session, attributes);
        },
        pos_partner_load_fields: function () {
            return _.find(this.models, function (model) {
                return model.model === 'res.partner';
            }).fields;
        },
        pos_partner_load_res_partner_domain: function () {
            return _.find(this.models, function (model) {
                return model.model === 'res.partner';
            }).domain;
        },
        pos_partner_load_domain: function () {
            console.log(this.pos_partner_load_res_partner_domain())
            return this.pos_partner_load_res_partner_domain().concat([['write_date', '>', this.db.get_partner_write_date()]]);
        },
        load_new_partners: function () {
            var self = this;
            var def = new $.Deferred();
            var fields = self.pos_partner_load_fields() ;
            var domain = self.pos_partner_load_domain();
            rpc.query({
                model: 'res.partner',
                method: 'search_read',
                args: [domain, fields],
            }, {
                timeout: 3000,
                shadow: true,
            }).then(function (partners) {
                    if (self.db.add_partners(partners)) {   // check if the partners we got were real updates
                        def.resolve();
                    } else {
                        def.reject();
                    }
                }, function (type, err) {
                    def.reject();
                });
            return def;
        }
    });
    return exports;
});