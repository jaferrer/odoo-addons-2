odoo.define('web_timeline_prohibit_creation.TimelineView', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var time = require('web.time');
    var session = require('web.session');
    var TimelineView = require('web_timeline.TimelineView');


    TimelineView.include({

        init_timeline: function () {
            var self = this;
            var res_super = self._super();
            var add = false;
            if (self.ViewManager.action.context.create != 'undefined') {
                if (self.permissions['create'] == true) {
                    if (self.ViewManager.action.context.create == true) {
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
            var options = {
                editable: {
                    // add new items by double tapping
                    add: add
                }
            };
            self.timeline.setOptions(options);
        }
    })
})
;