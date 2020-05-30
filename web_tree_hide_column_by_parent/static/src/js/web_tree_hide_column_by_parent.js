openerp.web_tree_hide_column_by_parent = function(instance) {
	instance.web.ListView.include({
	    load_list: function(data) {
			this._super(data);
			this.show_column_by_parent()
		},
        show_column_by_parent: function () {
            var self = this;
            this.visible_columns = _.filter(this.columns, function (column) {
                var to_show = true;
                if (column.column_invisible_parent) {
                    var domain = instance.web.pyeval.eval('domains', [column.column_invisible_parent])
                    var ParentRecord = self.ViewManager.ActionManager.getParent().datarecord;
                    var res = _.filter(domain, function (condition) {
                        var fieldkey = condition[0];
                        var symbol = condition[1];
                        var value = condition[2];
                        if (symbol == '=') {
                            symbol = "==";
                        }
                        var to_eval = "'" + ParentRecord[fieldkey] + "' " + symbol + " '" + value + "'";
                        evalres = eval(to_eval);
                        return evalres
                    })
                    if (domain.length == res.length) {
                        to_show = false
                    }
                }
                if (to_show == false) {
                    $('th[data-id="' + column.name + '"]').addClass('oe_form_invisible');
                    $('td[data-field="' + column.name + '"]').addClass('oe_form_invisible')
                }
                return to_show;
            });
	    }
	});
}

