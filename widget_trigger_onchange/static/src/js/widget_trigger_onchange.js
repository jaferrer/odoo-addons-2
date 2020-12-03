odoo.define('widget_trigger_onchange.trigger_onchange', function (require) {
    "use strict";

    var core = require('web.core')
    var common = require('web.form_common');

    var WidgetTriggerOnchange = common.AbstractField.extend({
        events: {
            "click": "onclick"
        },

        init: function(field_manager, node) {
            this._super(field_manager, node);
            this.string = this.options['text'] || node.name;
            this.help = this.options['help'] || "";
        },

        start: function() {
            return this._super();
        },

        render_value: function () {
            this._super();
            this.$el.html(core.qweb.render("TriggerOnchangeTemplate", {widget: this}));
        },

        onclick: function() {
            this.internal_set_value(!this.get_value());
        },
    });

    core.form_widget_registry.add('trigger_onchange', WidgetTriggerOnchange);
});