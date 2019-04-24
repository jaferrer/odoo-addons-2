'use strict';
openerp.view_form_improved = function(instance) {
    /**
     * Prevents read request for one2many fields when invisible.
     */

    // instance.web.BufferedDataSet = instance.web.BufferedDataSet.extend({
    instance.web.BufferedDataSet.include({
        read_ids: function (ids, fields, options) {
            let isHidden = (this.o2m !== undefined) && $.inArray("oe_form_invisible", this.o2m.el.classList) !== -1;
            if (isHidden) {
                console.log("[BufferedDataSet.invisible]" + this.model + "." + this.o2m.name);
                return this._super([], fields, options)
            }
            return this._super(ids, fields, options)
        }
    });
    //instance.web.BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;
};

