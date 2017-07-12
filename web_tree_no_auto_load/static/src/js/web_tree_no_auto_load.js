openerp.web_tree_no_auto_load = function(instance) {
	instance.web.SearchView.include({

        init: function(parent, dataset, view_id, defaults, options) {
	        this.events['click button.oe_searchview_search'] = function (e) {
                e.stopImmediatePropagation();
                this.do_search('on_click_oe_searchview_search');
            };
            this._super(parent, dataset, view_id, defaults, options)
        },

        do_search: function (_query, options) {
            var parent_context = this.getParent().action.context;
            if (parent_context && parent_context.no_auto_load
                && _query !== 'on_click_oe_searchview_search') {
                return
            }
            this._super(_query, options);
        }
	});
}

