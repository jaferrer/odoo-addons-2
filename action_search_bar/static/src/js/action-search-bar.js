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
            this._super(parent);
            this.options = _.clone(options) || {};
        },
        searchAction: function () {
            var self = this;
            self.action_manager = new instance.web.ActionManager(self);
            var search_value = $('input.action_search_bar_searchbox').val();
            $('input.action_search_bar_searchbox').val("");
            self.rpc("/web/action/load", { action_id: "action_search_bar.action_search_bar_results" }).done(function(result) {
                result.res_id =  instance.session.uid;
                result.domain = "[('name', 'ilike', '%"+search_value+"%')]";
                return self.action_manager.do_action(result);
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