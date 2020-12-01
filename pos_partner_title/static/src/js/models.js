odoo.define('pos_partner_title.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');

    models.load_fields("res.partner", ["title"]);

});
