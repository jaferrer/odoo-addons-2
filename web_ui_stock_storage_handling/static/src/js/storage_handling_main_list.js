odoo.define('web_ui_stock_storage_handling.StorageHandlingMainWidget', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');

    var StorageHandlingMainWidget = Widget.extend({
        template: 'StorageHandlingMainWidget',
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.storageScreen = true;
            this.pickingName = options.picking_name || "";
            this.pickingId = options.picking_id || false;
        },
        renderElement: function () {
            this._super();
            this.$('#btn_exit').click((ev) => window.history.back());
            this.$('#create_chariot').click((ev) => { this.open_scan_product_main_widget() });
            this.$('#clean_chariot').click((ev) => { this.open_storage_main_widget() });
            this.$('#back_to_choice').click((ev) => { this.back_to_choice() });
            this.$('#direct_clean').click((ev) => { this.direct_clean() });
            // Si on veut ranger un chariot qu'on vient de créer
            if (this.pickingId) {
                this.$('#big_helper').addClass('hidden');
                this.$('#ask_for_direct_clean').removeClass('hidden');
            }
        },
        open_scan_product_main_widget: function () {
            this.$('#big_helper').parent().parent().empty();
            this.do_action('stock.ui.product', {
                'picking_type_id': this.pickingTypeId,
                'storage_screen': this.storageScreen,
            });
        },
        open_storage_main_widget: function () {
            this.$('#big_helper').parent().parent().empty();
            this.do_action('stock.ui.storage', {
                'picking_type_id': this.pickingTypeId,
                'storage_screen': this.storageScreen,
                'picking_id': this.pickingId,
            });
        },
        back_to_choice: function () {
            // On revient à l'écran de choix
            this.$('#ask_for_direct_clean').addClass('hidden');
            this.$('#big_helper').removeClass('hidden');
            this.pickingName = "";
            this.pickingId = false;
        },
        direct_clean: function () {
            // On passe au rangement du chariot en mémoire
            this.$('#big_helper').parent().parent().empty();
            this.open_storage_main_widget()
        },
    });

    core.action_registry.add('stock.ui.storage_handling', StorageHandlingMainWidget);
    return StorageHandlingMainWidget;
});
