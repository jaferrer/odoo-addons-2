odoo.define('web_progressbar_colored', function(require) {
'use strict';

var BasicFields = require('web.basic_fields');

BasicFields.FieldProgressBar.include({

    _render_value: function (v) {
        this._super.apply(this, arguments);

        var value = this.value;
        if (!isNaN(v)) {
            if (!this.edit_max_value) {
                value = v;
            }
        }
        value = value || 0;

        // Ajout d'une classe pour gérer la couleur de la barre
        var valueClass = 'o_progressbar_color_normal';
        if (value > 100 && value <= 110) {
            valueClass = 'o_progressbar_color_warning';
        }
        else if (value > 110) {
            valueClass = 'o_progressbar_color_danger';
        }
        this.$('.o_progressbar_complete').addClass(valueClass);
    },
});

});



