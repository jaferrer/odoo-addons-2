openerp.web_fixed_headers = function(instance) {
	
	var _lt = openerp.web._lt;
	var _t = openerp.web._t;
	
	instance.web.ListView.List.include({
		
		$table : null,
		$header : null,
		widthcol :[],
		
		init: function (group, opts) {
			this._super(group, opts);
			this.$table=$('.oe_view_manager_view_list table.oe_list_content:first');
			this.$table.addClass('fixed_headers');
		},
		
		resize_list_content :function () {
			var self=this;
			
			if(this.$table.find('tbody tr:first').children().size()>0) {
			
				if($('.oe_view_manager_view_list table.oe_list_header_custom:first').size()<1) {
					var $tbody = this.$table.find('tbody tr:first').children();
				    this.widthcol = $tbody.map(function() {
				        return $(this).width();
				    }).get();
					console.log($('.oe_view_manager_view_list table.oe_list_header_custom:first').size());
					this.$table.before("<table class='oe_list_header_custom'></table>");
					this.$header=$('.oe_view_manager_view_list table.oe_list_header_custom:first');
					var $thead=this.$table.find('thead');
					this.$header.append($thead.clone());
					$thead.css({'visibility':'collapse'});
					
					this.$header.find('tr').children().each(function(i, v) {
				    	$(v).width(self.widthcol[i]);
				    });
					
					this.$table.height($(document).find("div.oe_view_manager_body:first").height()-this.$header.height()-2);
				
				}
			    console.log("resize");
			} else {
				var self=this;
				window.setTimeout(function() {
		        	self.resize_list_content()
		        },500);
			}
		},
		
		render: function () {
	        this._super();
	        this.resize_list_content()	
	    }
	    
	});
}

