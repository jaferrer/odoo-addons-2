odoo.define('avis_verifies.form_widgets', function (require) {
"use strict";

var core = require('web.core');
var common = require('web.form_common');

var AvisVerifiesWidget = common.AbstractField.extend({
    start: function () {
        var url = this.get('value');
        var widget = $('<iframe></iframe>');
        widget.attr({
            'id': 'AV_widget_iframe',
            'class': 'av-widget',
            'frameBorder': 0,
            'src': url,
        });
        this.$el.append(widget);
    }
});

/**
 * Registry of form fields, called by :js:`instance.web.FormView`.
 *
 * All referenced classes must implement FieldInterface. Those represent the classes whose instances
 * will substitute to the <field> tags as defined in OpenERP's views.
 */
core.form_widget_registry.add('av_widget', AvisVerifiesWidget);

});
