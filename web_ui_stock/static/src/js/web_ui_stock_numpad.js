odoo.define('web_ui_stock.Numpad', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    let modalId = '#numpad-modal';

    return Widget.extend({
        template: 'LineNumpad',
        init: function (row, name="") {
            $(modalId).remove();
            this._super(row);
            this.row = row;
            this.unit = '';
            this.name = name;
            this.qty_initial = 0;
            this.qty_value = 0;
            this.qty_todo = null;
            this.is_placeholder_visible = true;
        },
        start: function () {
            this._super();
            $(modalId).modal();
            this.clear_numpad();
        },
        renderElement: function () {
            this._super();
            console.log("Numpad renderElement");
            this.$('#validate_new_qty').click(ev => { this.validate_and_exit() });
            this.$('#exit_numpad').click(ev => { this.exit() });
            this.$('#numpad_add_0').click(ev => { this.add_number("0") });
            this.$('#numpad_add_1').click(ev => { this.add_number("1") });
            this.$('#numpad_add_2').click(ev => { this.add_number("2") });
            this.$('#numpad_add_3').click(ev => { this.add_number("3") });
            this.$('#numpad_add_4').click(ev => { this.add_number("4") });
            this.$('#numpad_add_5').click(ev => { this.add_number("5") });
            this.$('#numpad_add_6').click(ev => { this.add_number("6") });
            this.$('#numpad_add_7').click(ev => { this.add_number("7") });
            this.$('#numpad_add_8').click(ev => { this.add_number("8") });
            this.$('#numpad_add_9').click(ev => { this.add_number("9") });
            this.$('#numpad_add_coma').click(ev => { this.add_coma() });
            this.$('#numpad_backspace').click(ev => { this.remove_number() });
        },
        add_number: function (str) {
            if (this.is_placeholder_visible) {
                this.$('#numpad_new_quantity').text("");
                this.qty_value = 0;
                this.is_placeholder_visible = false;
            }
            this.qty_value += str;
            this.qty_value = parseFloat(this.qty_value);
            this.$('#numpad_new_quantity').text(this.qty_value);
        },
        add_coma: function () {
            if (!this.is_placeholder_visible && this.qty_value.toString().indexOf(".") === -1) {
                this.qty_value += ".";
                this.$('#numpad_new_quantity').text(this.qty_value);
            }
        },
        remove_number: function () {
            if (!this.is_placeholder_visible && this.qty_value.toString().length > 1) {
                this.qty_value = this.qty_value.toString().substring(0, this.qty_value.toString().length-1);
                this.qty_value = parseFloat(this.qty_value);
                this.$('#numpad_new_quantity').text(this.qty_value);
            }
            else {
                this.clear_numpad();
            }
        },
        clear_numpad: function () {
            this.$('#numpad_new_quantity').html('<span class="placeholder">' + this.qty_initial + '</span>');
            this.qty_value = this.qty_initial;
            this.is_placeholder_visible = true;
        },
        set_display_quantity: function () {
            this.$('#numpad_quantity').text(this.qty_value);
        },
        validate_and_exit: function (ev) {
            this.row.validate_new_qty(this.qty_value);
            this.exit();
        },
        exit: function (ev) {
            $(modalId).modal('hide');
        },
    });
});
