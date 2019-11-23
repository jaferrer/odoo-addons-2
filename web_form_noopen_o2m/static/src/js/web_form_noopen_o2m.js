odoo.define('web_form_noopen_o2m.FormNoopenO2m', function (require) {
    "use strict";
    var core = require('web.core');
    // Juste pour être sûr que le fichier est loadé avant celui-ci
    require('web.form_relational');
    console.log(core.one2many_view_registry.map.list);

    core.one2many_view_registry.map.list.include({
        do_activate_record: function(index, id) {
            if (this.x2m.options.no_open_form !== undefined && this.x2m.options.no_open_form === true &&
                this.x2m.get("effective_readonly") && typeof id === "number") {
                return;
            }
            this._super(index, id);
        }

    })
});