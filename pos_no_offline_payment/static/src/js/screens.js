odoo.define('pos_no_offline_payment.screens', function (require) {
    "use strict";

    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var _t = core._t;


    models.PosModel = models.PosModel.extend({
        push_order: function (order, opts) {
            opts = opts || {};
            var self = this;
            var orders = []

            if (order) {
                this.db.add_order(order.export_as_JSON());
                orders = [this.db.get_order(order.uid)]
            }

            var pushed = new $.Deferred();

            this.flush_mutex.exec(function () {
                var flushed = self._flush_orders(orders, opts);

                flushed.done(function (ids) {
                    pushed.resolve();
                });

                flushed.fail(function (ids) {
                    pushed.reject()
                })

                return flushed;
            });
            return pushed;
        },

    })

    screens.PaymentScreenWidget.include({
        init: function (parent, options) {
            var self = this;
            this._super(parent, options);
            setInterval(self.show_connection, 2000);
        },
        show_connection: function () {
            console.log("show_connection");
            if (navigator.onLine) {
                $('.js_connected').removeClass('oe_hidden');
                $('.js_disconnected').addClass('oe_hidden');
            } else {
                $('.js_connected').addClass('oe_hidden');
                $('.js_disconnected').removeClass('oe_hidden');
            }
        },
        validate_order: function (force_validation) {
            var self = this;
            if (!navigator.onLine) {
                self.gui.show_popup('error',
                    {
                        'title': _t('Error: You are offline'),
                        'body': _t('Can not save payment, please try again when you are connected to the internet'),
                    });
            } else {
                self._super(force_validation)
            }
        },
        finalize_validation: function () {
            var self = this;
            var order = this.pos.get_order();

            if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

                this.pos.proxy.open_cashbox();
            }

            order.initialize_validation_date();
            order.finalized = true;

            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;
                invoiced.fail(function (error) {
                    self.invoicing = false;
                    order.finalized = false;
                    if (error.message === 'Missing Customer') {
                        self.gui.show_popup('confirm', {
                            'title': _t('Please select the Customer'),
                            'body': _t('You need to select the customer before you can invoice an order.'),
                            confirm: function () {
                                self.gui.show_screen('clientlist');
                            },
                        });
                    } else if (error.code < 0) {        // XmlHttpRequest Errors
                        self.gui.show_popup('error', {
                            'title': _t('The order could not be sent'),
                            'body': _t('Check your internet connection and try again.'),
                        });
                    } else if (error.code === 200) {    // OpenERP Server Errors
                        self.gui.show_popup('error-traceback', {
                            'title': error.data.message || _t("Server Error"),
                            'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
                        });
                    } else {                            // ???
                        self.gui.show_popup('error', {
                            'title': _t("Unknown Error"),
                            'body': _t("The order could not be sent to the server due to an unknown error"),
                        });
                    }
                });

                invoiced.done(function () {
                    self.invoicing = false;
                    order.finalize();
                });
            } else {
                this.pos.push_order(order).done(function (res) {
                    self.gui.show_screen('receipt');
                }).fail(function (error) {
                    console.log("Fail connection server :", error);
                    self.gui.show_popup('error', {
                        'title': _t('Error: Unable to access the server'),
                        'body': _t('Can not save payment, Please try again later or contact the administrator.'),
                    });
                })
            }
        },
    });
});