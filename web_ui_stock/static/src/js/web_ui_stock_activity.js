odoo.define('web_ui_stock.StockActivity', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');

    var StockActivity = Widget.extend({
        template: 'StockActivity',
        fragmentsStack: [],
        activityContainer: null,
        backButton: null,
        pickingTypeId: null,
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
        },
        renderElement: function() {
            this._super();

            this.activityContainer = this.$('#activity-container');
            this.backButton = this.$('#back-btn');

            this.$('#exit-btn').click((ev) => {
                this.exit_activity();
            });

            this.backButton.click((ev) => {
                this.return_to_previous_fragment();
            });
        },
        set_activity_title: function (title) {
            this.$("#view_title").text(title);
        },
        init_title: function () {
            throw new Error("Vous devez implementer la méthode");
        },
        init_fragment: function () {
            this.activityContainer.empty();
            if (this.fragmentsStack.length > 1) {
                this.backButton.removeClass('hidden');
            }
            else {
                this.backButton.addClass('hidden');
            }
        },
        exit_activity: function () {
            window.history.back();
        },
        return_to_previous_fragment: function () {
            if (this.fragmentsStack.length <= 1) {
                return;
            }
            this.fragmentsStack.pop().destroy();
            this.init_fragment();
            this.fragmentsStack[this.fragmentsStack.length - 1].appendTo(this.activityContainer);
        }
    });

    core.action_registry.add('stock.ui.stock', StockActivity);
    return StockActivity;
});
