odoo.define('web_ui_stock_receipt.ReceiptMoveLineRow', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var Model = require('web.Model');
    let StockMoveLine = new Model('stock.pack.operation');
    var Numpad = require('web_ui_stock_receipt.ReceiptMoveLineNumpad');

    return Widget.extend({
        template: 'ReceiptMoveLineRow',
        init: function (receiptMainList, move_line) {
            this._super(receiptMainList);
            this.receiptMainList = receiptMainList;
            this.id = move_line.id;
            this.move_line = move_line;
            this.product = move_line.product;
            this.quantity_to_do = move_line.quantity;
            this.quantity_done = 0;
            this.display_qty = this.quantity_done + "/" + this.quantity_to_do;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ProductTableRow renderElement");
            this.$().click(ev => { new Numpad(this).appendTo('body'); });
        },
        update_quantity: function () {
            this.quantity_done += 1;
            this.display_qty = this.quantity_done + "/" + this.quantity_to_do;
            this.check_qty();
            this.$('#move_line_quantity').text(this.display_qty);
        },
        qty_higher: function () {
            this.$().removeClass('text-success');
            this.$().removeClass('text-warning');
            this.$().addClass('text-danger');
            this.$().addClass('font-weight-bold');
            this.receiptMainList.move_line_rows.forEach((move_line_row) => {
                move_line_row.$('#confirm_qty_body').addClass('hidden')
            });
            this.$('button.js_confirm_qty').addClass('hidden');
        },
        qty_lower: function () {
            this.$().removeClass('text-success');
            this.$().addClass('text-warning');
            this.$().removeClass('text-danger');
            this.$().addClass('font-weight-bold');
            this.receiptMainList.move_line_rows.forEach((move_line_row) => {
                move_line_row.$('#confirm_qty_body').removeClass('hidden')
            });
            this.$('button.js_confirm_qty').removeClass('hidden');
        },
        qty_right: function () {
            this.$().addClass('text-success');
            this.$().removeClass('text-warning');
            this.$().removeClass('text-danger');
            this.$().removeClass('font-weight-bold');
            this.receiptMainList.move_line_rows.forEach((move_line_row) => {
                move_line_row.$('#confirm_qty_body').removeClass('hidden')
            });
            this.$('button.js_confirm_qty').removeClass('hidden');
        },
        check_qty: function () {
            if (this.quantity_done > this.quantity_to_do) {
                this.qty_higher();
            }
            else if (this.quantity_done < this.quantity_to_do) {
                this.qty_lower();
            }
            else if (this.quantity_done === this.quantity_to_do) {
                this.qty_right();
            }
        },
        validate_new_qty: function (qty) {
            this.quantity_done = parseFloat(qty);
            this.display_qty = this.quantity_done + "/" + this.quantity_to_do;
            this.check_qty();
            this.$('#move_line_quantity').text(this.display_qty);
        },
        confirm_qty: function () {
            this.$('button.js_confirm_qty').addClass('hidden');
            this.$().addClass('text-success');
            this.$().removeClass('text-warning');
            this.$().removeClass('font-weight-bold');
            this.receiptMainList.$('#manual_scan_product').toggleClass('hidden');
            this.receiptMainList.$('#manual_scan_product').removeClass('warning-background');
            this.receiptMainList.$('#manual_scan_picking').toggleClass('hidden');
            // Si l'on a pas pris la quantité demandée, crée une nouvelle ligne avec la quantité restante à faire
            if (this.quantity_done !== this.quantity_to_do) {
                this.receiptMainList.create_new_move_line(this);
                this.quantity_to_do = this.quantity_done;
                this.display_qty = this.quantity_done + "/" + this.quantity_to_do;
                this.$('#move_line_quantity').text(this.display_qty);
            }
        },
    });
});
