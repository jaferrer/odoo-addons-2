odoo.define("pos_change_contact.contact", function (require) {
    "use strict";
    var models = require("point_of_sale.models");

    models.load_fields("pos.config", ["crm_team_id"]);

    models.load_models([
        {
            model: 'crm.team',
            condition: function(self){ return !!self.config.crm_team_id[0]; },
            fields: ['contact_name', 'contact_email', 'contact_website', 'contact_phone', 'contact_vat', 'contact_address'],
            domain: function(self){ return [['id','=',self.config.crm_team_id[0]]]; },
            loaded: function(self,crm_teams){
                self.crm_team = crm_teams[0];
            },
        }
    ],{'after': 'pos.config'});


    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function () {
            var json = _super_order.export_for_printing.apply(this, arguments);
            json.contact = {
                contact_name: this.pos.crm_team.contact_name,
                contact_email: this.pos.crm_team.contact_email,
                contact_website: this.pos.crm_team.contact_website,
                contact_phone: this.pos.crm_team.contact_phone,
                contact_vat: this.pos.crm_team.contact_vat,
                contact_address: this.pos.crm_team.contact_address,
            };
            return json;
        },
    });
});