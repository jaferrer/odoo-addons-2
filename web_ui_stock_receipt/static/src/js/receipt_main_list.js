odoo.define('web_ui_stock_receipt.ReceiptMainWidget', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var ReceiptOwnerSelection = require('web_ui_stock_receipt.ReceiptOwnerSelection');
    var ReceiptPickingSelection = require('web_ui_stock_receipt.ReceiptPickingSelection');
    var ReceiptMoveLine = {
        Row: require('web_ui_stock_receipt.ReceiptMoveLineRow'),
        Result: require('web_ui_stock_receipt.ReceiptResult')
    };
    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');
    let StockPickingReceipt = new Model('stock.picking');
    let StockMoveLine = new Model('stock.pack.operation');

    var ReceiptMainWidget = Widget.extend({
        template: 'ReceiptMainWidget',
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.selection_stock_pickings = [];
            this.selected_receipt_picking = false;
            this.move_line_rows = [];
            this.changing_location = false;
            this.selected_scan_receipt_computer = 0;
            this.barcode_scanner = new BarcodeScanner();
            this.scanned_row = false;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            this.$('#btn_exit').click((ev) => {
                this.exit_scan()
            });
            this.$('button.js_validate_receipt').click((ev) => {
                this.do_validate_receipt()
            });
            this.receipt_picking_selection_table = this.$('#receipt_picking_selection_table');
            this.move_line_table_body = this.$('#move_line_table_body');
            this.receipt_result = this.$('#receipt_result');
            StockPickingType.call('name_get', [[this.pickingTypeId]]).then((res) => this._set_view_title(res[0][1]));

            this._load_receipt_pickings();
            this._connect_scanner_product();

            this.$('#search_product').focus(() => {
                this._disconnect_scanner();
                this.$('#search_product').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan_product(this.$('#search_product').val())
                    }
                })
            });
            this.$('#search_product').blur(() => {
                this.$('#search_product').off('keyup');
                this._connect_scanner_product();
            });
            this.$('#clear_search_product').click(() => {
                console.log('clear_search_product');
                this.$('#search_product').val('');
                this.$('#search_product').focus()
            });
        },
        _load_receipt_pickings: function () {
            let self = this;
            StockPickingReceipt.call('get_receipt_grouped_pickings', [])
                .then((owner_list) => {
                    owner_list.forEach((value) => {
                        let selection_row = new ReceiptOwnerSelection(self, value);
                        selection_row.appendTo(this.receipt_picking_selection_table);

                        value.stock_pickings.forEach((value) => {
                            let move_line_row = new ReceiptPickingSelection(self, value);
                            this.selection_stock_pickings.push(move_line_row);
                            move_line_row.appendTo(selection_row.$('.owner-stock-pickings'));
                        });
                    });
                });
        },
        _load_receipt_move_lines: function (picking_id) {
            StockPickingReceipt.call('get_receipt_move_lines', [[picking_id]])
                .then((move_line_list) => {
                    move_line_list.forEach((value) => {
                        let move_line_row = new ReceiptMoveLine.Row(this, value);
                        this.move_line_rows.push(move_line_row);
                        move_line_row.appendTo(this.move_line_table_body);
                    });
                    this.scanned_row = this.move_line_rows[0];
                });
        },
        _set_view_title: function (title) {
            $("#view_title").text(title);
        },
        _connect_scanner_product: function () {
            this.barcode_scanner.connect(this.scan_product.bind(this));
        },
        _disconnect_scanner: function () {
            this.barcode_scanner.disconnect();
        },
        get_header: function () {
            return this.getParent().get_header();
        },
        scan_product: function (name) {
           console.log(name);
            this.$('#search_product').val('');
            StockPickingType.call('web_ui_get_product_info_by_name', [[this.pickingTypeId], name])
                .always(() => {
                    if (!this.$('#big_helper').hasClass('hidden')) {
                        this.$('#big_helper').addClass('hidden')
                    }
                })
                .then((produ) => {
                    let productsIds = this.move_line_rows.map(it => it.product.id);
                    if (!productsIds.includes(produ.id)) {
                        // Pas dans liste
                    } else {
                        let row = this.move_line_rows.find(it => it.product.id == produ.id);
                        if (row.product.tracking !== 'serial') {
                            row.update_quantity();
                        }
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    event.preventDefault();
                });
        },
        create_new_move_line: function (move_line_row) {
            let qty_left = move_line_row.quantity_to_do - move_line_row.quantity_done;
            StockMoveLine.call('create_move_line_from_scan_receipt', [[move_line_row.id], qty_left])
                .then((new_move_line_value) => {
                    let new_move_line_row = new ReceiptMoveLine.Row(this, new_move_line_value);
                    this.move_line_rows.push(new_move_line_row);
                    new_move_line_row.appendTo(this.move_line_table_body);
                });
        },
        do_validate_receipt: function () {
            let product_infos = [];
            this.move_line_rows.forEach(row => product_infos.push({
                'id': row.product.id,
                'quantity': row.quantity_done}
                ));
            StockPickingReceipt.call('do_validate_receipt', [[this.selected_receipt_picking], product_infos])
                .then((result) => {
                    this.receipt_result.empty();
                    new ReceiptMoveLine.Result(this, result).appendTo(this.receipt_result);
                    $('#receipt-result').modal();
                    // window.history.back()
                });
        },
        exit_scan: function () {
            // Enlève les doublons de move lines à terminer si on arrête l'application en plein milieu d'une séquence
            if (this.selected_receipt_picking) {
                StockMoveLine.call('do_clear_siblings_move_lines_receipt', [[this.scanned_row.id]])
                    .then(console.log('aaaaaaa'));
            }
            window.history.back();
        },
    });


    core.action_registry.add('stock.ui.receipt', ReceiptMainWidget);
    return ReceiptMainWidget;
});
