odoo.define('web_mrp_timeline.TimelineView', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var time = require('web.time');
    var session = require('web.session');
    var TimelineView = require('web_timeline.TimelineView');


    TimelineView = View.include({

         init_timeline: function () {
             var self = this;
             var res_super = self._super();
             var add = false;
             if (self.fields_view.arch.attrs.create != 'undefined') {
                 if (self.permissions['create'] == true) {
                     if (self.fields_view.arch.attrs.create == 'true') {
                         add = true;
                     } else {
                         add = false;
                     }
                 } else {
                     add = false;
                 }
             } else {
                 add = self.permissions['create'];
             }
             self.options.editable.add = add;
             self.timeline.setOptions(self.options);
     });
});