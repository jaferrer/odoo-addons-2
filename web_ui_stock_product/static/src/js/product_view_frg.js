odoo.define('web_ui_stock_product.ProductView', function (require) {
    "use strict";
    var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
    var ProductRow = {
        Row: require('web_ui_stock_product.ProductRow'),
        Error: require('web_ui_stock_product.ProductRow.Error'),
        Lot: require('web_ui_stock_product.ProductRow.Lot')
    };
    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');
    let ProductProduct = new Model('product.product');
    let Widget = require('web.Widget');

    const STATES = {
        product: 1,
        location: 2,
        lot: 3
    }

    return Widget.extend(BarcodeHandlerMixin, {
        template: 'ProductView',
        activity: null,
        ownerId: null,
        state: STATES.product,
        rows: [],
        lot_row: false,
        currentProduct: null,
        init: function (activity, ownerId) {
            this._super.apply(this, arguments);
            BarcodeHandlerMixin.init.apply(this, arguments);
            this.activity = activity;
            this.ownerId = ownerId ? parseInt(ownerId) : null;
        },
       renderElement: function() {
            this._super();
            this.productBlock = this.$('#product-block');
            this.product_table_body = this.$('#product_table_body');
            this.needLot = this.$('#need_for_lot');
            this.codeInput = this.$('#search-code');

            this.$('#clear-search-code').click(() => {
                this.codeInput.val('');
                this.codeInput.focus();
            });
            this.$('#btn_delete_all_rows').click(() => {
                this.$('.line-error').remove()
                this.rows.forEach((row) => row.deleteRow());
            });
            this.renderState();
        },
        registerValidation: function() {
            $('#validate-activity').off('click')
            $('#validate-activity').click(ev => {
                this.validate_scan()
            });
        },
        start: function () {
            this._super();
            this.init_title();
        },
        init_title: function () {
            StockPickingType.call('name_get', [[this.activity.pickingTypeId]]).then((res) => this.activity.set_activity_title(res[0][1]));
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
        on_barcode_scanned: function (value) {
            console.log(value);
            this.codeInput.val('');
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
        scan: function (ean) {
            return this.on_barcode_scanned(ean)
        }, //Compatibility
        scanProduct: function (value) {
            StockPickingType.call('web_ui_get_product_info_by_name', [[this.activity.pickingTypeId], value, false, this.activity.is_internal_move])
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
                        if (row.product.tracking !== 'serial' && !this.activity.auto_max_qty) {
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
            StockPickingType.call('web_ui_get_production_info_for_product', [[this.activity.pickingTypeId], value, this.lot_row.productRow.product.id])
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
            StockPickingType.call('web_ui_get_location_info_by_name_batch', [[this.activity.pickingTypeId], value])
                .then((produ) => {
                    this.currentProduct.product.location_id = produ.id
                    this.currentProduct.product.location_barcode = produ.barcode
                    this.currentProduct.renderElement();
                    this.state = STATES.product
                    this.renderState();
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    this.activity.notifyError("Mauvais emplacement");
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
            var queryParams = [[this.activity.pickingTypeId], product_infos]
            if (this.ownerId) {
                queryParams.push(this.ownerId);
            }
            StockPickingType.call('do_validate_scan', queryParams)
                .then((picking) => {
                    if (this.activity.is_internal_move) {
                        this.activity.continue_to_storage(picking)
                    } else {
                        this.activity.back_to_handling_screen(picking)
                    }
                });
        },
        renderState: function () {
            $('#validate-activity').removeClass('hidden');
            this.registerValidation();
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
        }
    });
});
