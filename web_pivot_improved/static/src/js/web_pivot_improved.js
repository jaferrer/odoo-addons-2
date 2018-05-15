odoo.define('web_pivot_improved.PivotView', function (require) {
    "use strict";

    var core = require('web.core');
    var Model = require('web.DataModel');
    var time = require('web.time');
    var _ = require('_');
    var $ = require('$');
    var session = require('web.session');

    var _t = core._t;

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    var PivotView = require("web.PivotView");
    PivotView.include({
        sanitize_value: function (value, field) {
            if (value === false && this.fields[field].type === 'boolean') {
                return this.fields[field].string + _t(": no")
            }
            if (value === true && this.fields[field].type === 'boolean') {
                return this.fields[field].string + _t(": yes")
            }
            if (value === false && this.fields[field].type !== 'boolean') {
                return _t("Undefined")
            }
            return this._super(value, field);
        },
    });
})
;