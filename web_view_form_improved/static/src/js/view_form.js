'use strict';
openerp.web_view_form_improved = function (instance) {
    /**
     * Prevents read request for one2many fields when invisible.
     */

    // instance.web.BufferedDataSet = instance.web.BufferedDataSet.extend({
    instance.web.BufferedDataSet.include({
        read_ids: function (ids, fields, options) {
            var self = this;
            if (this.hasOwnProperty('o2m')) {
//                console.log(this);
//                console.log("-------------------------------- this.o2m : ", this.child_name, ids);
                arguments[0] = [];
                var invisible  = false;
                if (this.o2m.modifiers.invisible !== undefined)
                    invisible = this.o2m.field_manager.compute_domain(this.o2m.modifiers.invisible);
                var args = arguments;
//                console.log("BEFORE SUPER : ", this.o2m.el.classList, $.inArray("oe_form_invisible", this.o2m.el.classList) === -1);
//                console.log("EVAL INVISIBLE FIELD : ", invisible);
                 //if ($.inArray("oe_form_invisible", self.o2m.el.classList) === -1) {
                 if (!invisible) {
//                     console.log("READ : ", ids);
                     args[0] = ids;
                 }
                var res = self._super.apply(self, args);
//                console.log("res: ", res)
                return res
            }
            else{
                return self._super.apply(this, arguments);
            }
        }
    });
    //instance.web.BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;
};

