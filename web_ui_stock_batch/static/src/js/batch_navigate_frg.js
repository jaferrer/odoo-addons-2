odoo.define('web_ui_stock_batch.BatchNavigate', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Numpad = require('web_ui_stock_batch.BatchNumpad');
    var Model = require('web.Model');
    let StockPickingBatch = new Model('stock.picking.wave');
    let StockPickingType = new Model('stock.picking.type');
    let StockMoveLine = new Model('stock.pack.operation');

    const STATES = {
        location : 1,
        product : 2,
        picking : 3
    }

    return Widget.extend({
        template: 'BatchNavigate',
        barcode_scanner: null,
        activity: null,
        batchId: null,
        moveLineId: null,
        moveLine: null,
        nextLineId: null,
        codeInput: null,
        state: STATES.location,
        showManualInput: 1,
        hasQtyChanged: false,
        init: function (activity, batchId, options = {}, currentMoveLine = null) {
            this._super();
            this.barcode_scanner = new BarcodeScanner();
            this.activity = activity;
            this.batchId = parseInt(batchId);
            this.moveLineId = currentMoveLine ? parseInt(currentMoveLine) : '';

            this.state = options.skipFirstStep ? STATES.product : this.state;
            this.showManualInput = options.showManualInput;
        },
        renderElement: function () {
            this._super();
            this.codeInput = this.$('#search-code');

            this.$('#skip-move-line-btn').click(ev => {
                if (this.state === STATES.picking) {
                    this.next_move_line();
                }
                else if (this.hasQtyChanged) {
                    this.state = STATES.picking;
                    this.renderState();
                }
                else {
                   this.next_move_line();
                }
            });

            this.$('#end-navigation-btn').click(ev => {
                this.end_navigation();
            });

            this.$('.picking-nav .picking-flex').click(ev => {
                if (this.state === STATES.location) {
                    this.scan("");
                }
                else if (this.state === STATES.product) {
                    new Numpad(this, this.moveLine.product.name).appendTo('body');
                }
            });

            this.renderState();
            this.renderQty();
            this.register_scanner();
        },
        start: function () {
            this._super();
            this.init_navigation();
        },
        destroy: function () {
            this.barcode_scanner.disconnect();
            this._super();
        },
        register_scanner: function () {
            this.barcode_scanner.disconnect();
            this.codeInput.focus(() => {
                this.barcode_scanner.disconnect();
                this.codeInput.on('keyup', (e) => {
                    if (e.key === 'Enter') {
                        this.scan($(this.codeInput).val())
                    }
                })
            });
            this.codeInput.blur(() => {
                this.codeInput.off('keyup');
                this.barcode_scanner.connect(this.scan.bind(this));
            });
            this.barcode_scanner.connect(this.scan.bind(this));
        },
        init_title: function () {
            StockPickingBatch.call('read', [[this.batchId], ['name']]).then((res) => {
                this.activity.set_activity_title(res[0]['name']);
            });
        },
        init_navigation: function () {
            StockPickingBatch.call('get_batch_move_line', [[this.batchId], this.moveLineId])
                .then((moveLine) => {
                    this.moveLine = moveLine;
                    this.moveLineId = moveLine.id;
                    this.nextLineId = moveLine.next_move_line_id;
                    this.init_title();
                    this.renderElement();
                }).fail((errors, event) => {
                    let message = errors.data ? errors.data.message : "Une erreur est survenue"
                    this.activity.notifyError(message);
                    event.preventDefault();
                });
        },
        validate_new_qty: function (qty) {
            this.hasQtyChanged = true;
            this.moveLine.qty_done = parseFloat(qty);
            this.renderQty();
            if (this.moveLine.qty_done === this.moveLine.qty_todo) {
                this.state = STATES.picking;
                this.renderState();
            }
        },
        next_move_line: function () {
            if (!this.nextLineId) {
                this.end_navigation();
            }
            else {
                this.activity.init_fragment_batch_navigate(this.batchId, this.nextLineId);
            }
        },
        end_navigation: function() {
            this.activity.init_fragment_batch_recap(this.batchId);
        },
        scan: function (code) {
            console.log(code);

            let goToNextStep = false;
            this.codeInput.val('');

            switch (this.state) {
                case STATES.location:
                    this.scanLocation(code);
                    goToNextStep = true;
                    break;
                case STATES.product:
                    this.scanProduct(code);
                    break;
                case STATES.picking:
                    this.scanPicking(code);
                    break;
            }

            if (goToNextStep) {
                if (this.state === STATES.picking) {
                    this.next_move_line();
                }
                this.state++;
                this.renderState();
            }
        },
        scanLocation: function (code) {
            return true;
        },
        scanProduct: function (code) {
            StockPickingType.call('web_ui_get_product_info_by_name', [[this.activity.pickingTypeId], code])
                .then((product) => {
                        if (this.moveLine.product.name === product.name) {
                            this.validate_new_qty(this.moveLine.qty_done + 1);
                        } else {
                            this.activity.notifyError("Mauvais produit");
                        }
                    }
                )
                .fail((errors, event) => {
                    this.activity.notifyError("Produit introuvable");
                    event.preventDefault();
                });
        },
        scanPicking: function (code) {
            StockMoveLine.call('web_ui_update_odoo_qty_batch', [[this.moveLineId], this.moveLine.qty_done, code])
                .then(() => {
                    this.next_move_line();
                })
                .fail((errors, event) => {
                    let message = errors.data ? errors.data.message : "Une erreur est survenue"
                    this.activity.notifyError(message);
                    event.preventDefault();
                });
        },
        renderButton: function () {
            if (this.state === STATES.picking) {
                this.$('#skip-move-line-btn').text("Annuler et passer");
            }
            else if (this.hasQtyChanged) {
                this.$('#skip-move-line-btn').text("Je ne sais pas ou est le reste");
            } else {
                this.$('#skip-move-line-btn').text("Passer ce produit");
            }
        },
        renderQty: function () {
            // Gestion de l'affichage de la quantité uniquement
            if (!this.moveLine) {
                return;
            }

            this.$('#picking-qty-done').text(this.moveLine.qty_done);

            if (this.moveLine.qty_done === this.moveLine.qty_todo) {
                this.$('#picking-qty-done').addClass('text-success');
            } else if (this.moveLine.qty_done > this.moveLine.qty_todo) {
                this.$('#picking-qty-done').addClass('text-danger');
            } else {
                this.$('#picking-qty-done').removeClass('text-success');
                this.$('#picking-qty-done').removeClass('text-danger');
            }

            this.renderButton();
        },
        renderState: function () {
            switch (this.state) {
                case STATES.location:
                    this.renderStateLocation();
                    break;
                case STATES.product:
                    this.renderStateProduct();
                    break;
                case STATES.picking:
                    this.renderStatePicking();
                    break;
            }
            this.renderButton();
        },
        renderStateLocation: function () {
            this.$('#picking-location').addClass('picking-focus');
            this.$('#picking-product').removeClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-name').removeClass('picking-focus');

            this.$('#info-text').text("Allez à l'emplacement demandé");
        },
        renderStateProduct: function () {
            this.$('#picking-location').removeClass('picking-focus');
            this.$('#picking-product').addClass('picking-focus');
            this.$('#picking-qty-done').addClass('picking-focus');
            this.$('#picking-name').removeClass('picking-focus');

            this.$('#info-text').text("Prennez les articles demandés");
        },
        renderStatePicking: function () {
            this.$('#picking-location').removeClass('picking-focus');
            this.$('#picking-product').removeClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-name').addClass('picking-focus');

            this.$('#info-text').text("Scanner la commande demandée");
        },
    });
});