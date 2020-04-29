// Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as
//    published by the Free Software Foundation, either version 3 of the
//    License, or (at your option) any later version.
//    
//    This program is distributed in the hope that it will be useful,
//    
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//    
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.
//

odoo.define("pos_required_customer.Main", function (require) {
    "use strict";
    var pos_model = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var _t = require('web.core')._t;

    pos_model.load_fields("product.product", ['required_customer']);

    screens.PaymentScreenWidget.include({
        order_is_valid: function (force_validation) {
            const result = this._super(force_validation);
            if (!force_validation && !this.pos.get_client() && result) {
                for (const line of this.pos.get_order().get_orderlines()) {
                    if (line.product.required_customer) {
                        this.gui.show_popup('error', {
                            'title': _t('Required Customer'),
                            'body': _t(line.product.display_name + ' need a customer to be selled'),
                        });
                        return false;
                    }
                }
            }
            return result;
        }
    })
});

