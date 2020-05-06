odoo.define('web_ui_stock_product.ScanProductRow.Numpad', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require('web.WebClient');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'ProductTableRow.Numpad',
        init: function (productMainList, productRow) {
            this._super(productMainList);
            this.productMainList = productMainList;
            this.productRow = productRow;
            this.quantity = productRow.product.quantity;
            this.value = 0;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ProductTableRow.Numpad renderElement");
            this.$('button.js_validate_new_qty').click(ev => { this.productRow.validate_new_qty(this) });
            this.$('button.js_exit_numpad').click(ev => { this.productMainList.exit_numpad(this) });
            this.$('button.js_numpad_add_0').click(ev => { this.add_number("0") });
            this.$('button.js_numpad_add_1').click(ev => { this.add_number("1") });
            this.$('button.js_numpad_add_2').click(ev => { this.add_number("2") });
            this.$('button.js_numpad_add_3').click(ev => { this.add_number("3") });
            this.$('button.js_numpad_add_4').click(ev => { this.add_number("4") });
            this.$('button.js_numpad_add_5').click(ev => { this.add_number("5") });
            this.$('button.js_numpad_add_6').click(ev => { this.add_number("6") });
            this.$('button.js_numpad_add_7').click(ev => { this.add_number("7") });
            this.$('button.js_numpad_add_8').click(ev => { this.add_number("8") });
            this.$('button.js_numpad_add_9').click(ev => { this.add_number("9") });
            this.$('button.js_numpad_validate').click(ev => { this.validate_numpad() });
            this.$('button.js_numpad_clear').click(ev => { this.clear_numpad() });
            this.$('button.js_numpad_add_coma').click(ev => { this.add_coma() });
            this.$('button.js_numpad_backspace').click(ev => { this.remove_number() });
        },
        add_number: function (str) {
            this.value += str;
            this.value = parseFloat(this.value);
            this.$('#numpad_new_quantity').text(this.value);
        },
        add_coma: function () {
            if (this.value.toString().indexOf(".") === -1) {
                this.value += ".";
                this.$('#numpad_new_quantity').text(this.value);
            }
        },
        remove_number: function () {
            if (this.value.toString().length > 1) {
                this.value = this.value.toString().substring(0, this.value.toString().length-1);
                this.value = parseFloat(this.value);
                this.$('#numpad_new_quantity').text(this.value);
            }
            else if (this.value.toString().length === 1) {
                this.value = 0;
                this.$('#numpad_new_quantity').text(this.value);
            }
        },
        clear_numpad: function () {
            this.value = 0;
            this.$('#numpad_new_quantity').text(this.value);
        },
        validate_numpad: function () {
            this.quantity = parseFloat(this.value);
            this.$('#numpad_quantity').text(this.quantity);
            this.clear_numpad()
        },
        action_exit: function (ev) {
            this.productMainList.exit_numpad(this)
        },
    });
});
