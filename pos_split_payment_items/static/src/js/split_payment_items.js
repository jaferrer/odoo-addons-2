odoo.define('pos_split_payment_items.split_payment_items', function (require) {
    "use strict";

    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    models.PosModel = models.PosModel.extend({});

    screens.ScreenWidget.include({
        renderElement: function () {
            var self = this;
            this._super();
            this.$('.split_line').click(function () {
                var $el = $(this);
                var order = self.pos.get_order();
                var neworder = new models.Order({}, {
                    pos: self.pos,
                    temporary: true,
                });
                neworder.set('client', order.get('client'));
                console.log('order : ', order);
                var splitby = parseInt($('#line_split_number').val())
                var ids = []
                $.each($('.orderline.selected'), function () {
                    if (parseInt($(this).data('id'))) {
                        ids.push(parseInt($(this).data('id')));
                    }
                })
                if((splitby > 2 && splitby != 'NaN')|| ids.length == 0){
                    self.gui.show_popup('error', {
                        'title': _t('Error'),
                        'body': _t('Please enter the number of lines to divide or select lines'),
                    });

                }
                else{

                    self.splitline($el, order, neworder, ids, splitby);
                }
            });
        },
        splitline: function ($el, order, neworder, ids, split_by) {
            var self = this;
            ids.forEach(function (line_id) {
                var line = order.get_orderline(parseInt(line_id));
                var new_line = line.clone();
                var initial_quantity = line.quantity;
                var new_quantity = line.quantity / split_by;
                order.remove_orderline(line);
                order.add_orderline(new_line);
                new_line.set_quantity(new_quantity);
                $el.replaceWith($(QWeb.render('SplitOrderline',{
                    widget: self,
                    line: new_line,
                    selected: false,
                    quantity: new_line.quantity,
                    id: new_line.id,
                })));
                var i = 1;
                var total_quantity = new_quantity;
                while (i < split_by) {
                    var add_line = new_line.clone();
                    order.add_orderline(add_line);
                    total_quantity += add_line.quantity
                    if(i+1 == split_by && total_quantity != initial_quantity){
                        var good_quantity = new_quantity+(initial_quantity-total_quantity);
                        add_line.set_quantity(good_quantity);
                    }
                    $el.replaceWith($(QWeb.render('SplitOrderline',{
                        widget: self,
                        line: add_line,
                        selected: false,
                        quantity: add_line.quantity,
                        id: add_line.id,
                    })));
                    i++;
                }
            })
            self.gui.show_screen(self.previous_screen);
        },
    });
});