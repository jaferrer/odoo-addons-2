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
		},
		
		resize_list_content :function () {
			var self=this;
			if(this.$table.find('tbody tr:first').children().size()>0) {
				var $active_view=$("div.oe_view_manager_current[data-view-type='list']");
				var $tbody = this.$table.find('tbody tr:first').children();
			    this.widthcol = $tbody.map(function() {
			        return $(this).width();
			    }).get();
				if($active_view.find('.oe_view_manager_view_list table.oe_list_header_custom:first').size()<1) {
					
					console.log($('.oe_view_manager_view_list table.oe_list_header_custom:first').size());
					this.$table.before("<table class='oe_list_header_custom'></table>");
					this.$header=$('.oe_view_manager_view_list table.oe_list_header_custom:first');
					this.$header.after("<div class='fixedwrapper fixed_headers'></div>");
					$('div.fixedwrapper').append(this.$table);
					var $thead=this.$table.find('thead');
					this.$header.append($thead.clone());
					$thead.css({'visibility':'collapse'});
					//console.log($active_view.find("div.oe_view_manager_body:first"));
				
				}
				this.$header=$('.oe_view_manager_view_list table.oe_list_header_custom:first');
			    this.$header.find('tr').children().each(function(i, v) {
			    	$(v).width(self.widthcol[i]-1);
			    });
			    $('div.fixedwrapper').height($active_view.find("div.oe_view_manager_body:first").height()-this.$header.height()-2);
				$active_view.find('.oe_view_manager_view_list table.oe_list_header_custom:first').css({"display":this.$table.css("display")});
			    //console.log("resize");
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

