odoo.define('web_ui_stock_batch.BatchMainWidget', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var BatchSelectionTable = require('web_ui_stock_batch.BatchSelectionTable');
    var BatchMoveLine = {
        Row: require('web_ui_stock_batch.BatchMoveLineRow'),
        Lot: require('web_ui_stock_batch.BatchMoveLineLot')
    };
    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');
    let StockPickingBatch = new Model('stock.picking.wave');
    let StockMoveLine = new Model('stock.pack.operation');

    var BatchMainWidget = Widget.extend({
        template: 'BatchMainWidget',
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.selection_rows = [];
            this.selected_batch = false;
            this.move_line_rows = [];
            this.changing_location = false;
            this.selected_scan_batch_computer = 0;
            this.barcode_scanner = new BarcodeScanner();
            this.scanned_row = false;
        },
        renderElement: function () {
            this._super();
            this.$('#btn_exit').click((ev) => {
                this.exit_scan()
            });
            this.$('#validate_batch').click((ev) => {
                this.do_validate_batch()
            });
            this.batch_selection_table_body = this.$('#batch_selection_table_body');
            this.move_line_table_body = this.$('#move_line_table_body');
            this.need_for_lot = this.$('#need_for_lot');
            this.lot_row = false;
            this.quantity_numpad = this.$('#quantity_numpad');
            StockPickingType.call('name_get', [[this.pickingTypeId]]).then((res) => this._set_view_title(res[0][1]));

            this._set_all_picking_batches();
            this._connect_scanner_product();

            this.$('#search_location').focus(() => {
                this._disconnect_scanner();
                this.$('#search_location').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan_location(this.$('#search_location').val(), this.changing_location)
                    }
                })
            });
            this.$('#search_location').blur(() => {
                this.$('#search_location').off('keyup');
                this._connect_scanner_location();
            });
            this.$('#clear_search_location').click(() => {
                console.log('clear_search_location');
                this.$('#search_location').val('');
                this.$('#search_location').focus()
            });

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

            this.$('#search_product_lot').focus(() => {
                this._disconnect_scanner();
                this.$('#search_product_lot').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan_lot(this.$('#search_product_lot').val())
                    }
                })
            });
            this.$('#search_product_lot').blur(() => {
                this.$('#search_product_lot').off('keyup');
                this._connect_scanner_lot();
            });
            this.$('#clear_search_product_lot').click(() => {
                console.log('clear_search_product_lot');
                this.$('#search_product_lot').val('');
                this.$('#search_product_lot').focus()
            });

            this.$('#search_picking').focus(() => {
                this._disconnect_scanner();
                this.$('#search_picking').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan_picking(this.$('#search_picking').val())
                    }
                })
            });
            this.$('#search_picking').blur(() => {
                this.$('#search_picking').off('keyup');
                this._connect_scanner_picking();
            });
            this.$('#clear_search_picking').click(() => {
                console.log('clear_search_picking');
                this.$('#search_picking').val('');
                this.$('#search_picking').focus()
            });

        },
        _set_view_title: function (title) {
            $("#view_title").text(title);
        },
        start: function () {
            this._super();
        },
        _connect_scanner_location: function () {
            this.barcode_scanner.connect(this.scan_location.bind(this));
        },
        _connect_scanner_product: function () {
            this.barcode_scanner.connect(this.scan_product.bind(this));
        },
        _connect_scanner_lot: function () {
            this.barcode_scanner.connect(this.scan_lot.bind(this));
        },
        _connect_scanner_picking: function () {
            this.barcode_scanner.connect(this.scan_picking.bind(this));
        },
        _disconnect_scanner: function () {
            this.barcode_scanner.disconnect();
        },
        get_header: function () {
            return this.getParent().get_header();
        },

        _set_all_picking_batches: function () {
            StockPickingBatch.call('get_all_picking_batches', [])
                .then((batch_list) => {
                    batch_list.forEach((value) => {
                        let selection_row = new BatchSelectionTable(this, value);
                        this.selection_rows.push(selection_row);
                        selection_row.appendTo(this.batch_selection_table_body);
                    });
                });
        },
        _load_batch_move_lines: function (batch_id) {
            StockPickingBatch.call('get_batch_move_lines', [[batch_id]])
                .then((move_line_list) => {
                    move_line_list.forEach((value) => {
                        let move_line_row = new BatchMoveLine.Row(this, value);
                        this.move_line_rows.push(move_line_row);
                        move_line_row.appendTo(this.move_line_table_body);
                    });
                    this.scanned_row = this.move_line_rows[0];
                });
        },
        scan_location: function (name, changing_location) {
            console.log(name);
            this.$('#search_location').val('');
            StockPickingType.call('web_ui_get_location_info_by_name_batch', [[this.pickingTypeId], name])
                .then((location) => {
                    if (!changing_location) {
                        if (this.scanned_row.move_line.location_barcode === location.barcode) {
                            this.scanned_row.$('#move_line_location').removeClass('font-weight-bold');
                            this.scanned_row.$('#move_line_location').removeClass('text-warning');
                            this.scanned_row.$('#move_line_location').removeClass('text-danger');
                            this.scanned_row.$('#move_line_location').addClass('text-success');
                            this.$('#manual_scan_location').toggleClass('hidden');
                            this.show_or_hide_change_location();
                            this.$('#helper_location').toggleClass('hidden');
                        } else {
                            this.scanned_row.$('#move_line_location').removeClass('text-warning');
                            this.scanned_row.$('#move_line_location').addClass('text-danger');
                        }
                    } else {
                        this.scanned_row.$('#move_line_location').removeClass('font-weight-bold');
                        this.scanned_row.$('#move_line_location').removeClass('text-danger');
                        this.scanned_row.$('#move_line_location').addClass('text-success');
                        this.scanned_row.update_location(location);
                        this.forbid_change_location();
                        this.$('#confirm_location_header').removeClass('hidden');
                        this.move_line_rows.forEach((move_line_row) => {
                            move_line_row.$('#confirm_location_body').removeClass('hidden')
                        });
                        this.scanned_row.$('button.js_confirm_location').removeClass('hidden')
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    this.scanned_row.$('#move_line_location').removeClass('text-warning');
                    this.scanned_row.$('#move_line_location').removeClass('text-success');
                    this.scanned_row.$('#move_line_location').addClass('font-weight-bold');
                    this.scanned_row.$('#move_line_location').addClass('text-danger');
                    if (changing_location) {
                        this.$('#manual_scan_location').addClass('warning-background');
                        this.$('#confirm_location_header').addClass('hidden');
                        this.move_line_rows.forEach((move_line_row) => {
                            move_line_row.$('#confirm_location_body').addClass('hidden')
                        });
                        this.scanned_row.$('button.js_confirm_location').addClass('hidden')
                    }
                    event.preventDefault();
                });
        },
        // Permet de changer l'emplacement si nécessaire
        show_or_hide_change_location: function () {
            this.$('#change_location_header').toggleClass('hidden');
            this.$('#confirm_location_header').toggleClass('hidden');
            this.move_line_rows.forEach((move_line_row) => {
                move_line_row.$('#change_location_body').toggleClass('hidden');
                move_line_row.$('#confirm_location_body').toggleClass('hidden')
            });
            this.scanned_row.$('button.js_change_location').toggleClass('hidden');
            this.scanned_row.$('button.js_confirm_location').toggleClass('hidden');
        },
        allow_change_location: function () {
            this.changing_location = true;
            this.$('#helper_location').addClass('hidden');
            this.$('#manual_scan_location').removeClass('hidden');
            this.$('#manual_scan_location').addClass('waiting-background');
            this.$('#scan_location_classic').addClass('hidden');
            this.$('#scan_location_change').removeClass('hidden');
        },
        forbid_change_location: function () {
            this.changing_location = false;
            this.$('#helper_location').removeClass('hidden');
            this.$('#manual_scan_location').addClass('hidden');
            this.$('#manual_scan_location').removeClass('waiting-background');
            this.$('#scan_location_classic').removeClass('hidden');
            this.$('#scan_location_change').addClass('hidden');
        },

        scan_product: function (name) {
            console.log(name);
            this.$('#search_product').val('');
            StockPickingType.call('web_ui_get_product_info_by_name', [[this.pickingTypeId], name])
                .then((product) => {
                    if
                    (this.scanned_row.move_line.product.name === product.name && this.scanned_row.quantity_done === 0) {
                        this.scanned_row.$('#move_line_product').removeClass('font-weight-bold');
                        this.scanned_row.$('#move_line_product').removeClass('text-warning');
                        this.scanned_row.$('#move_line_product').removeClass('text-danger');
                        this.scanned_row.$('#move_line_product').addClass('text-success');
                        this.scanned_row.$('#move_line_quantity').addClass('font-weight-bold');
                        this.scanned_row.$('#move_line_quantity').addClass('text-warning');
                        this.scanned_row.$('#move_line_uom').addClass('font-weight-bold');
                        this.scanned_row.$('#move_line_uom').addClass('text-warning');
                        this.$('#manual_scan_add_qty_1').toggleClass('hidden');
                        this.$('#manual_scan_add_qty_2').toggleClass('hidden');
                        this.$('#manual_scan_add_qty_3').toggleClass('hidden');
                        if (this.scanned_row.quantity_to_do !== 1) {
                            this.$('#change_qty_header').removeClass('hidden');
                            this.move_line_rows.forEach((move_line_row) => {
                                move_line_row.$('#change_qty_body').removeClass('hidden')
                            });
                            this.scanned_row.$('button.js_open_numpad').removeClass('hidden');
                        }
                        this.scanned_row.update_quantity();

                        // Prend en charge les numéros de série/lot des articles
                        if ((product.tracking === "lot" || product.tracking === "serial") &&
                            product.lot_id === false) {
                            this.open_need_num_lot(this.scanned_row);
                        } else {
                            this.scanned_row.$('#move_line_lot').addClass('text-success');
                        }
                    } else if
                    (this.scanned_row.move_line.product.name === product.name && this.scanned_row.quantity_done > 0) {
                        this.scanned_row.update_quantity();
                        if (this.$('#manual_scan_product').hasClass('warning-background')) {
                            this.$('#manual_scan_product').toggleClass('warning-background');
                        }
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    if (this.scanned_row.quantity_done === 0) {
                        this.scanned_row.$('#move_line_product').removeClass('text-warning');
                        this.scanned_row.$('#move_line_product').addClass('text-danger');
                    }
                    if (this.scanned_row.quantity_done > 0) {
                        this.$('#manual_scan_product').toggleClass('warning-background');
                    }
                    event.preventDefault();
                });
        },

        open_need_num_lot: function (scanned_row) {
            this.$('#move_line_table').addClass('hidden');
            this.$('#manual_scan_product').addClass('hidden');
            this.$('#manual_scan_lot').removeClass('hidden');
            this.need_for_lot.removeClass('hidden');
            let lot_row = new BatchMoveLine.Lot(this, scanned_row);
            this.lot_row = lot_row;
            lot_row.appendTo(this.need_for_lot);
        },
        scan_lot: function (name) {
            console.log(name);
            this.$('#search_product_lot').val('');
            StockPickingType.call('web_ui_get_production_info_for_product', [[this.pickingTypeId], name, this.lot_row.product.id])
                .then((product) => {
                    if (this.lot_row.product.id === product.id) {
                        this.lot_row.batchMoveLineRow.update_num_lot(product);
                        this.exit_need_num_lot();
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    this.$('#manual_scan_lot').removeClass('waiting-background');
                    this.$('#manual_scan_lot').addClass('warning-background');
                    this.lot_row.$('#invalid_lot_number_col').removeClass('hidden');
                    this.lot_row.$('#invalid_lot_number_header').removeClass('hidden');
                    this.lot_row.invalid_number = name;
                    this.lot_row.$('#invalid_lot_number_col').text(this.lot_row.invalid_number);
                    event.preventDefault();
                });
        },
        exit_need_num_lot: function () {
            this.$('#move_line_table').removeClass('hidden');
            this.$('#manual_scan_product').removeClass('hidden');
            this.$('#manual_scan_lot').addClass('hidden');
            this.need_for_lot.addClass('hidden');
            this.need_for_lot.empty();
        },
        create_new_move_line: function (move_line_row) {
            let qty_left = move_line_row.quantity_to_do - move_line_row.quantity_done;
            StockMoveLine.call('create_move_line_from_scan_batch', [[move_line_row.id], qty_left])
                .then((new_move_line_value) => {
                    let new_move_line_row = new BatchMoveLine.Row(this, new_move_line_value);
                    this.move_line_rows.push(new_move_line_row);
                    new_move_line_row.appendTo(this.move_line_table_body);
                });
        },

        scan_picking: function (name) {
            console.log(name);
            this.$('#search_picking').val('');
            StockPickingType.call('web_ui_get_picking_info_by_name_batch', [[this.pickingTypeId], name])
                .then((picking) => {
                    if (this.scanned_row.move_line.picking === picking) {
                        this.scanned_row.$('#move_line_picking').removeClass('font-weight-bold');
                        this.scanned_row.$('#move_line_picking').removeClass('text-warning');
                        this.scanned_row.$('#move_line_picking').removeClass('text-danger');
                        this.scanned_row.$('#move_line_picking').addClass('text-success');
                        this.$('#manual_scan_picking').toggleClass('hidden');
                        this.scanned_row.send_qty_done_to_odoo();
                        this.move_line_rows.shift();
                        this.scanned_row.destroy();
                        if (this.move_line_rows[0]) {
                            this.$('#manual_scan_location').toggleClass('hidden');
                            this.scanned_row = this.move_line_rows[0];
                        } else {
                            this.$('#batch_scan_done').toggleClass('hidden');
                            this.$('#validate_batch').removeClass('hidden')
                        }
                    } else {
                        this.scanned_row.$('#move_line_picking').removeClass('text-warning');
                        this.scanned_row.$('#move_line_picking').addClass('text-danger');
                    }
                });
        },

        do_validate_batch: function () {
            StockPickingBatch.call('do_validate_batch_scan', [[this.selected_batch.id]])
                .then(window.history.back());
        },

        exit_scan: function () {
            // Enlève les doublons de move lines à terminer si on arrête l'application en plein milieu d'une séquence
            if (this.selected_batch) {
                StockMoveLine.call('do_clear_siblings_move_lines_batch', [[this.scanned_row.id]])
                    .then(console.log('aaaaaaa'));
            }
            window.history.back()
        },

    });


    core.action_registry.add('stock.ui.batch', BatchMainWidget);
    return BatchMainWidget;
});
