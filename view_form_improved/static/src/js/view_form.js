'use strict';
openerp.view_form_improved = function (instance) {
    /**
     * Prevents read request for one2many fields when invisible.
     */

    // instance.web.BufferedDataSet = instance.web.BufferedDataSet.extend({
    instance.web.BufferedDataSet.include({
        read_ids: function (ids, fields, options) {
            var res = false;
            // this._check_visibility();
            if (this.hasOwnProperty('o2m')) {
                console.log("this.o2m.el.classList : ", this.o2m.el.classList);
                this.o2m._check_visibility();
                console.log("After visibility: ", this.o2m.el.classList);
                if ($.inArray("oe_form_invisible", this.o2m.el.classList) !== -1) {
                    console.log("____NO LOAD : ",  this.child_name, this.o2m.el.classList, ids, arguments);
                    arguments[0] = [];
                    res =  this._super.apply(this, arguments);
                }
                console.log("----LOAD : ",  this.child_name, this.o2m.el.classList, ids, arguments);
            }
            res = this._super.apply(this, arguments);

            console.log('res : ', res, this.o2m.el.classList)
            return res
        }
    });
    //instance.web.BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;
};

