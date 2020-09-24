odoo.define('web_ui_stock_product.ProductView', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var ProductRow = {
        Row: require('web_ui_stock_product.ProductRow'),
        Error: require('web_ui_stock_product.ProductRow.Error'),
        Lot: require('web_ui_stock_product.ProductRow.Lot')
    };
    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');
    let ProductProduct = new Model('product.product');

    const STATES = {
        product: 1,
        location: 2,
        lot: 3
    }

    var ProductView = Widget.extend({
        template: 'ProductView',
        state: STATES.product,
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.storageScreen = options.storage_screen || false;
            this.type = options.type || false;
            this.auto_max_qty = this.type === 'internal_move'
            this.rows = [];
            this.lot_row = false;
            this.barcode_scanner = new BarcodeScanner();
            this.currentProduct = null;
        },
        renderElement: function () {
            this._super();
            this.productBlock = this.$('#product-block');
            this.$('#btn_exit').click((ev) => window.history.back());
            this.product_table_body = this.$('#product_table_body');
            this.needLot = this.$('#need_for_lot');
            StockPickingType.call('name_get', [[this.pickingTypeId]]).then((res) => this.setTitle(res[0][1]));

            this.connectScanner();
            this.$('#search-code').focus(() => {
                this.disconnectScanner();
                this.$('#search-code').on('keyup', (e) => {
                    if (e.key === 'Enter') {
                        this.scan(this.$('#search-code').val())
                    }
                })
            });
            this.$('#search-code').blur(() => {
                this.$('#search-code').off('keyup');
                this.connectScanner();
            });

            this.$('#clear-search-code').click(() => {
                this.$('#search-code').val('');
                this.$('#search-code').focus();
            });
            this.$('#btn_delete_all_rows').click(() => {
                this.$('.line-error').remove()
                this.rows.forEach((row) => row.deleteRow());
            });
            this.$('button.js_validate_scan').click(ev => {
                this.validate_scan()
            });

            // Si on arrive sur cet écran depuis le gestionnaire de chariot
            if (this.storageScreen) {
                this.$('#back_to_handling_screen').removeClass('hidden');
            }
            this.$('#back_to_handling_screen').click(() => {
                this.back_to_handling_screen()
            });
        },
        start: function () {
            this._super();
        },
        setTitle: function (title) {
            $("#view_title").text(title);
        },
        connectScanner: function () {
            this.barcode_scanner.connect(this.scan.bind(this));
        },
        disconnectScanner: function () {
            this.barcode_scanner.disconnect();
        },
        requestLocation: function (row) {
            this.currentProduct = row;
            this.state = STATES.location;
            this.renderState();
        },
        requestNumLot: function (row) {
            this.state = STATES.lot;
            this.renderState();
            ProductProduct.call('web_ui_get_product_info', [[row.product.id]])
                .then((result) => {
                    let lot_row = new ProductRow.Lot(this, row);
                    this.lot_row = lot_row;
                    lot_row.appendTo(this.needLot);
                });
        },
        requestProduct: function () {
            this.state = STATES.product;
            this.needLot.empty();
            this.renderState();
        },
        scan: function (value) {
            console.log("SCAN: " + value);
            this.$('#search-code').val('');
            switch (this.state) {
                case STATES.product:
                    this.scanProduct(value);
                    break;
                case STATES.lot:
                    this.scanLot(value);
                    break;
                case STATES.location:
                    this.scanLocation(value);
                    break;
            }
        },
        scanProduct: function (value) {
            StockPickingType.call('web_ui_get_product_info_by_name', [[this.pickingTypeId], value, false, this.type])
                .always(() => {
                    this.renderState();
                })
                .then((produ) => {
                    let productsIds = this.rows.map(it => it.product.id);
                    if (!productsIds.includes(produ.id)) {
                        let row = new ProductRow.Row(this, produ);
                        this.rows.push(row);
                        row.prependTo(this.product_table_body);
                    } else {
                        let row = this.rows.find(it => it.product.id === produ.id);
                        if (row.product.tracking !== 'serial' && !this.auto_max_qty) {
                            row.increaseQty();
                        }
                    }
                })
                .fail((errors, event) => {
                    new ProductRow.Error(this, {
                        'title': errors.data.arguments[0],
                        'message': errors.data.arguments[1]
                    }).appendTo(this.product_table_body);
                    event.preventDefault();
                });
        },
        scanLot: function (value) {
            StockPickingType.call('web_ui_get_production_info_for_product', [[this.pickingTypeId], value, this.lot_row.productRow.product.id])
                .then((produ) => {
                    let row = this.rows.find(it => it.product.id === produ.id);
                    if (row) {
                        row.updateNumLot(produ);
                        this.exit_need_num_lot();
                    } else if (row === undefined) {
                        this.lot_row.$('#invalid_lot_number_col').removeClass('hidden');
                        this.lot_row.$('#invalid_lot_number_header').removeClass('hidden');
                        this.lot_row.invalid_number = value;
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    this.lot_row.invalid_number = value;
                    event.preventDefault();
                    this.lot_row.$('#invalid_lot_number_col').text(value);
                    this.lot_row.$('#invalid_lot_number_col').removeClass('hidden');
                    this.lot_row.$('#invalid_lot_number_header').removeClass('hidden');
                });
        },
        scanLocation: function (value) {
            StockPickingType.call('web_ui_get_location_info_by_name_batch', [[this.pickingTypeId], value])
                .then((produ) => {
                    this.currentProduct.product.location_id = produ.id
                    this.currentProduct.product.location_barcode = produ.barcode
                    this.currentProduct.renderElement();
                    this.state = STATES.product
                    this.renderState();
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    $.toast({
                        text: "Mauvais emplacement",
                        icon: 'error'
                    });
                    event.preventDefault();
                });
        },
        removeRow: function (row) {
            this.rows.splice(this.rows.indexOf(row), 1);
        },
        validate_scan: function () {
            let product_infos = [];
            this.rows.forEach(row => product_infos.push({
                    'id': row.product.id,
                    'quantity': row.product.quantity,
                    'location_id': row.product.location_id,
                }
            ));
            StockPickingType.call('do_validate_scan', [[this.pickingTypeId], product_infos])
                .then((pickingName) => {
                    if (this.type === 'internal_move') {
                        this.continue_to_storage(pickingName)
                    } else {
                        this.back_to_handling_screen(pickingName)
                    }
                });
        },
        back_to_handling_screen: function (pickingName = "") {
            this.do_action('stock.ui.storage_handling', {
                'picking_type_id': this.pickingTypeId,
                'picking_name': pickingName
            });
        },
        continue_to_storage: function (pickingName) {
            this.do_action('stock.ui.storage', {
                'picking_type_id': this.pickingTypeId,
                'storage_screen': this.storageScreen,
                'picking_name': pickingName,
            });
        },
        renderState: function () {
            this.$('#title-intro').addClass('hidden');
            switch (this.state) {
                case STATES.product:
                    this.productBlock.removeClass('hidden');
                    this.needLot.addClass('hidden');
                    this.$('#title-scan-product').removeClass('hidden');
                    this.$('#title-scan-lot').addClass('hidden');
                    this.$('#title-scan-location').addClass('hidden');
                    this.$('#big_helper').addClass('alert-info');
                    this.$('#big_helper').removeClass('alert-danger');
                    break;
                case STATES.lot:
                    this.productBlock.addClass('hidden');
                    this.needLot.removeClass('hidden');
                    this.$('#title-scan-product').addClass('hidden');
                    this.$('#title-scan-lot').removeClass('hidden');
                    this.$('#title-scan-location').addClass('hidden');
                    this.$('#big_helper').removeClass('alert-info');
                    this.$('#big_helper').addClass('alert-danger');
                    break;
                case STATES.location:
                    this.productBlock.removeClass('hidden');
                    this.needLot.addClass('hidden');
                    this.$('#title-scan-product').addClass('hidden');
                    this.$('#title-scan-lot').addClass('hidden');
                    this.$('#title-scan-location').removeClass('hidden');
                    this.$('#big_helper').removeClass('alert-info');
                    this.$('#big_helper').addClass('alert-danger');
                    break;
            }
        },
    });

    core.action_registry.add('stock.ui.product', ProductView);
    return ProductView;
});
