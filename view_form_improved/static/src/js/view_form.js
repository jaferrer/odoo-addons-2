'use strict';
openerp.view_form_improved = function (instance) {
    /**
     * Prevents read request for one2many fields when invisible.
     */

    // instance.web.BufferedDataSet = instance.web.BufferedDataSet.extend({
    instance.web.BufferedDataSet.include({
        read_ids: function (ids, fields, options) {
            var self = this;
            if (this.hasOwnProperty('o2m')) {
                console.log("-------------------------------- this.o2m : ", this.child_name, ids);
                arguments[0] = [];
                var t = 0;
                var args = arguments;
                console.log("BEFORE SUPER : ", this.o2m.el.classList, $.inArray("oe_form_invisible", this.o2m.el.classList) === -1);
                var res = false;
                res = this._super.apply(this, arguments).done(function () {

                    console.log("AFTER SUPER : ", self.o2m.el.classList, $.inArray("oe_form_invisible", self.o2m.el.classList));
                    if ($.inArray("oe_form_invisible", self.o2m.el.classList) === -1) {
                        console.log("READ : ", ids);
                        args[0] = ids;
                        res = self._super.apply(self, args);
                        console.log("sub res : ", res)
                    }
                    console.log("Final SUPER : ", self.o2m.el.classList, $.inArray("oe_form_invisible", self.o2m.el.classList));
                });
                console.log("res: ", res)
                return res
            }
            else{
                return self._super.apply(this, arguments);
            }
        }
    });
    //instance.web.BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;
};

