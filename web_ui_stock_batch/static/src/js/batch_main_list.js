odoo.define('web_ui_stock_batch.BatchMainWidget', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var BatchSelectionTable = require('web_ui_stock_batch.BatchSelectionTable');
    var BatchMoveLine = {
        Row: require('web_ui_stock_batch.BatchMoveLineRow'),
        Lot: require('web_ui_stock_batch.BatchMoveLineLot'),
        Numpad: require('web_ui_stock_batch.BatchMoveLineNumpad')
    };
    var rpc = require('web.rpc');

    var BatchMainWidget = Widget.extend(AbstractAction.prototype, {
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
            this.$('#_exit').click((ev) => window.history.back());
            this.$('button.js_validate_batch').click((ev) => { this.do_validate_batch() });
            this.batch_selection_table_body = this.$('#batch_selection_table_body');
            this.move_line_table_body = this.$('#move_line_table_body');
            this.need_for_lot = this.$('#need_for_lot');
            this.lot_row = false;
            this.quantity_numpad = this.$('#quantity_numpad');
            let spt_name_get_params = {
                model: 'stock.picking.type',
                method: 'name_get',
                args: [[this.pickingTypeId]],
            };
            rpc.query(spt_name_get_params).then((res) => this._set_view_title(res[0][1]));
            this._set_all_picking_batches();
            this._init_scan_batch_computer();
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
        _init_scan_batch_computer: function () {
            let printer_computer_params = {
                model: 'poste.batch',
                method: 'search_read',
                args: [[]],
            };
            rpc.query(printer_computer_params).then((res) => {
                let scan_batch_section = this.$('#scan_batch_printer_choice');
                res.forEach(res => {
                    scan_batch_section.append($(document.createElement('button'))
                        .addClass('btn')
                        .addClass('btn-default')
                        .addClass('btn-scan-batch')
                        .attr('data-scan-batch-computer-id', res.id)
                        .attr('data-scan-batch-computer-code', res.code)
                        .text(res.name)
                    );
                });
                this.$('button.btn-scan-batch').click((ev) => this.on_select_scan_batch_computer(ev));
            });
        },
        on_select_scan_batch_computer: function (ev) {
            let el = $(ev.currentTarget);
            this.$('button.btn-scan-batch').removeClass('btn-success');
            this.$('button.btn-scan-batch').addClass('btn-default');
            el.toggleClass('btn-success');
            el.toggleClass('btn-default');
            this.selected_scan_batch_computer = el.data('scan-batch-computer-id');
            this.$('#btn_process_all_rows').prop("disabled", false);
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
            let spb_batch_info_params = {
                model: 'stock.picking.batch',
                method: 'get_all_picking_batches',
                args: [],
            };
            rpc.query(spb_batch_info_params)
                .then((batch_list) => {
                    batch_list.forEach((value) => {
                      let selection_row = new BatchSelectionTable(this, value);
                      this.selection_rows.push(selection_row);
                      selection_row.appendTo(this.batch_selection_table_body);
                    });
                });
        },
        _load_batch_move_lines: function (batch_id) {
          let spb_batch_move_line_info_params = {
                model: 'stock.picking.batch',
                method: 'get_batch_move_lines',
                args: [[batch_id]],
          };
          rpc.query(spb_batch_move_line_info_params)
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
            let sl_location_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_location_info_by_name_batch',
                args: [[this.pickingTypeId], name],
            };
            rpc.query(sl_location_info_params)
                .then((location) => {
                    if (!changing_location) {
                        if (this.scanned_row.move_line.location_barcode === location.barcode) {
                            this.scanned_row.$('#move_line_location').removeClass('font-weight-bold');
                            this.scanned_row.$('#move_line_location').removeClass('text-warning');
                            this.scanned_row.$('#move_line_location').removeClass('text-danger');
                            this.scanned_row.$('#move_line_location').addClass('text-success');
                            this.$('#manual_scan_location').toggleClass('d-none');
                            this.show_or_hide_change_location();
                            this.$('#helper_location').toggleClass('d-none');
                        }
                        else {
                            this.scanned_row.$('#move_line_location').removeClass('text-warning');
                            this.scanned_row.$('#move_line_location').addClass('text-danger');
                        }
                    }
                    else {
                        this.scanned_row.$('#move_line_location').removeClass('font-weight-bold');
                        this.scanned_row.$('#move_line_location').removeClass('text-danger');
                        this.scanned_row.$('#move_line_location').addClass('text-success');
                        this.scanned_row.update_location(location);
                        this.forbid_change_location();
                        this.$('#confirm_location_header').removeClass('d-none');
                        this.move_line_rows.forEach((move_line_row) => {
                            move_line_row.$('#confirm_location_body').removeClass('d-none')
                        });
                        this.scanned_row.$('button.js_confirm_location').removeClass('d-none')
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
                            this.$('#confirm_location_header').addClass('d-none');
                            this.move_line_rows.forEach((move_line_row) => {
                                move_line_row.$('#confirm_location_body').addClass('d-none')
                            });
                            this.scanned_row.$('button.js_confirm_location').addClass('d-none')
                        }
                    event.preventDefault();
                });
        },
        // Permet de changer l'emplacement si nécessaire
        show_or_hide_change_location: function () {
            this.$('#change_location_header').toggleClass('d-none');
            this.$('#confirm_location_header').toggleClass('d-none');
            this.move_line_rows.forEach((move_line_row) => {
                move_line_row.$('#change_location_body').toggleClass('d-none');
                move_line_row.$('#confirm_location_body').toggleClass('d-none')
            });
            this.scanned_row.$('button.js_change_location').toggleClass('d-none');
            this.scanned_row.$('button.js_confirm_location').toggleClass('d-none');
        },
        allow_change_location: function () {
            this.changing_location = true;
            this.$('#helper_location').addClass('d-none');
            this.$('#manual_scan_location').removeClass('d-none');
            this.$('#manual_scan_location').addClass('waiting-background');
            this.$('#scan_location_classic').addClass('d-none');
            this.$('#scan_location_change').removeClass('d-none');
        },
        forbid_change_location: function () {
            this.changing_location = false;
            this.$('#helper_location').removeClass('d-none');
            this.$('#manual_scan_location').addClass('d-none');
            this.$('#manual_scan_location').removeClass('waiting-background');
            this.$('#scan_location_classic').removeClass('d-none');
            this.$('#scan_location_change').addClass('d-none');
        },

        scan_product: function (name) {
            console.log(name);
            this.$('#search_product').val('');
            let spt_product_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_product_info_by_name',
                args: [[this.pickingTypeId], name],
            };
            rpc.query(spt_product_info_params)
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
                        this.$('#manual_scan_add_qty_1').toggleClass('d-none');
                        this.$('#manual_scan_add_qty_2').toggleClass('d-none');
                        this.$('#manual_scan_add_qty_3').toggleClass('d-none');
                        if (this.scanned_row.quantity_to_do !== 1) {
                            this.$('#change_qty_header').removeClass('d-none');
                            this.move_line_rows.forEach((move_line_row) => {
                                move_line_row.$('#change_qty_body').removeClass('d-none')
                            });
                            this.scanned_row.$('button.js_open_numpad').removeClass('d-none');
                        }
                        this.scanned_row.update_quantity();

                        // Prend en charge les numéros de série/lot des articles
                        if ((product.tracking === "lot" || product.tracking === "serial") &&
                            product.lot_id === false) {
                            this.open_need_num_lot(this.scanned_row);
                        }
                        else {
                            this.scanned_row.$('#move_line_lot').addClass('text-success');
                        }
                    }
                    else if
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
            this.$('#move_line_table').addClass('d-none');
            this.$('#manual_scan_product').addClass('d-none');
            this.$('#manual_scan_lot').removeClass('d-none');
            this.need_for_lot.removeClass('d-none');
            let lot_row = new BatchMoveLine.Lot(this, scanned_row);
            this.lot_row = lot_row;
            lot_row.appendTo(this.need_for_lot);
        },
        scan_lot: function (name) {
            console.log(name);
            this.$('#search_product_lot').val('');
            let spt_product_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_production_info_for_product',
                args: [[this.pickingTypeId], name, this.lot_row.product.id],
            };
            rpc.query(spt_product_info_params)
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
                    this.lot_row.$('#invalid_lot_number_col').removeClass('d-none');
                    this.lot_row.$('#invalid_lot_number_header').removeClass('d-none');
                    this.lot_row.invalid_number = name;
                    this.lot_row.$('#invalid_lot_number_col').text(this.lot_row.invalid_number);
                    event.preventDefault();
                });
        },
        exit_need_num_lot: function () {
            this.$('#move_line_table').removeClass('d-none');
            this.$('#manual_scan_product').removeClass('d-none');
            this.$('#manual_scan_lot').addClass('d-none');
            this.need_for_lot.addClass('d-none');
            this.need_for_lot.empty();
        },

        open_numpad: function (scanned_row) {
            let scanned_row_numpad = new BatchMoveLine.Numpad(this, scanned_row);
            scanned_row_numpad.appendTo(this.quantity_numpad);
            this.$('#move_line_table').toggleClass('d-none');
            this.$('#mass_btn').toggleClass('d-none');
            this.quantity_numpad.toggleClass('d-none');
        },
        exit_numpad: function () {
            this.$('#move_line_table').toggleClass('d-none');
            this.$('#mass_btn').toggleClass('d-none');
            this.quantity_numpad.toggleClass('d-none');
            this.quantity_numpad.empty();
        },
        create_new_move_line: function (move_line_row) {
            let qty_left = move_line_row.quantity_to_do - move_line_row.quantity_done;
            let sml_new_move_line_info_params = {
                model: 'stock.move.line',
                method: 'create_move_line_from_scan_batch',
                args: [[move_line_row.id], qty_left],
            };
            rpc.query(sml_new_move_line_info_params)
                .then((new_move_line_value) => {
                    let new_move_line_row = new BatchMoveLine.Row(this, new_move_line_value);
                    this.move_line_rows.push(new_move_line_row);
                    new_move_line_row.appendTo(this.move_line_table_body);
            })
        },

        scan_picking: function (name) {
            console.log(name);
            this.$('#search_picking').val('');
            let sp_picking_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_picking_info_by_name_batch',
                args: [[this.pickingTypeId], name],
            };
            rpc.query(sp_picking_info_params)
                .then((picking) => {
                    if (this.scanned_row.move_line.picking === picking) {
                        this.scanned_row.$('#move_line_picking').removeClass('font-weight-bold');
                        this.scanned_row.$('#move_line_picking').removeClass('text-warning');
                        this.scanned_row.$('#move_line_picking').removeClass('text-danger');
                        this.scanned_row.$('#move_line_picking').addClass('text-success');
                        this.$('#manual_scan_picking').toggleClass('d-none');
                        this.scanned_row.send_qty_done_to_odoo();
                        this.move_line_rows.shift();
                        this.scanned_row.destroy();
                        if (this.move_line_rows[0]) {
                            this.$('#manual_scan_location').toggleClass('d-none');
                            this.scanned_row = this.move_line_rows[0];
                        }
                        else {
                            this.$('#batch_scan_done').toggleClass('d-none');
                            this.$('button.js_validate_batch').removeClass('d-none')
                        }
                    }
                    else {
                        this.scanned_row.$('#move_line_picking').removeClass('text-warning');
                        this.scanned_row.$('#move_line_picking').addClass('text-danger');
                    }
                });
        },

        do_validate_batch: function () {
            let do_validate_batch_params = {
                model: 'stock.picking.batch',
                method: 'do_validate_batch_scan',
                args: [[this.selected_batch.id]],
            };
            rpc.query(do_validate_batch_params).then(() => { window.history.back() })
        },
    });


    core.action_registry.add('stock.ui.batch', BatchMainWidget);
    return BatchMainWidget;
});
