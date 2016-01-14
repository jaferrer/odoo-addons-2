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
			if(this.$table.find('tbody:not(.oe_group_header) tr:not(.oe_group_header):first').children().size()>0) {
				var $active_view=$("div.oe_view_manager_current[data-view-type='list']");
				var $tbody = this.$table.find('thead tr:first').children();
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
					console.log($(".openerp .oe_view_manager_body"));
					 $(".openerp .oe_view_manager_body").scroll(function () {
						 $('div.fixedwrapper').css({"left":$(this).scrollLeft()+"px"})
						 $('div.fixedwrapper').scrollLeft($(this).scrollLeft());
					 });
				}
				this.$header=$('.oe_view_manager_view_list table.oe_list_header_custom thead');
			    this.$header.find('tr').children().each(function(i, v) {
			    	if($(v).attr("width")!="1"){
			    		var node;
			    		if($(v).attr('class')==undefined){
			    			var text=$(v).text();
			    			$(v).text("");
			    			$(v).append("<div>"+text+"</div>");
			    		}
			    		node=$(v).children().first();
			    		if(i<self.widthcol.length-1){
			    			node.css({'width':self.widthcol[i]});
			    		}else{
			    			node.css({'width':self.widthcol[i]+9});
			    		}
			    	}
			    });
			    $('div.fixedwrapper').css({"height":$active_view.find("div.oe_view_manager_body:first").height()-this.$header.height()-15,"width": "100%","position":"absolute"});
				$active_view.find('.oe_view_manager_view_list table.oe_list_header_custom:first').css({"display":this.$table.css("display")});
				
				this.$header.find('.oe_list_record_selector').click(function(){
					self.group.view.$el.find('.oe_list_record_selector input').prop('checked',
							self.group.view.$el.find('.oe_list_record_selector').prop('checked')  || false);
		            var selection = self.group.view.groups.get_selection();
		            $(self.group.view.groups).trigger(
		                'selected', [selection.ids, selection.records]);
		        });
				
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

