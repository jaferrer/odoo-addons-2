(function () {

    "use strict";

    var instance = openerp;
    var _t = openerp._t;
    var _lt = openerp._lt;
    var QWeb = openerp.qweb;
    var action_search_bar = openerp.action_search_bar = {};

    action_search_bar.SearchBarManager = openerp.Widget.extend({
        template: 'action_search_bar.TopSearchForm',
        events: {
            "click i.trigger_search": "searchAction",
            "submit": "searchAction",
        },
        init: function (parent, options) {
            var self = this;
            this._super(parent);
            this.options = _.clone(options) || {};
        },
        searchAction: function (params) {
        var self = this;
            console.log("search : ", params)
            alert("Search")
            // actions_windows = new instance.web.Model('ir.action.window')
            //                 .filter([['production_id', 'in', productions_ids]])
            //                 .all()
            self.rpc("/web/action/load", { action_id: "base.action_res_users_my" }).done(function(result) {
                result.res_id =  instance.session.uid;
                console.log('result : ',result)
                console.log('self.getParent() ; ', self.getParent())
                console.log('action manager ', self.getParent().action_manager)
                return self.getParent().do_action(result);

            });

        }
    });
    if (openerp.web && openerp.web.UserMenu) {
        openerp.web.UserMenu.include({
            do_update: function () {
                var button = new openerp.action_search_bar.SearchBarManager(this);
                button.prependTo(window.$('.oe_systray'));
                return this._super.apply(this, arguments);
            }
        })
    }
    return action_search_bar
})();