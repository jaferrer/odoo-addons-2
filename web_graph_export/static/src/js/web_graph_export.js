openerp.web_graph_export = function(instance) {
	
	var _lt = openerp.web._lt;
	var _t = openerp.web._t;
	
	instance.web_graph.Graph.include({
		
		start: function() {
			this._super();
			this.$(".graph_options_selection .btn-default[data-choice='export_data']:first").css({'display':''});
			
		},
		
		option_selection: function (event) {
			this._super(event);
	        event.preventDefault();
	        switch (event.currentTarget.getAttribute('data-choice')) {
	            case 'export_graph':
	                this.export_current_graph();
	                break;
	        }
	    },
	    
	 // ----------------------------------------------------------------------
	    // Controller stuff...
	    // ----------------------------------------------------------------------
	    export_current_graph: function() {
	        var c = openerp.webclient.crashmanager;
	        var s = new XMLSerializer();

	        var html=s.serializeToString(this.svg);
	        //console.log(html.replace("width=\""+this.width+"\"","").replace("height=\""+this.height+"\"","height=\"400\"").replace("<svg ","<svg viewBox=\"0 0 "+this.width+" "+this.height+"\" "));
	        html=html.replace("width=\""+this.width+"\"","").replace("height=\""+this.height+"\"","height=\"400\"").replace("<svg ","<svg viewBox=\"0 0 "+this.width+" "+this.height+"\" ");
	        //openerp.web.blockUI();
	        this.session.get_file({
	            url: '/web_graph_export/export_graph',
	            data: {
	            	data: window.btoa(unescape(html)),
	            	pivot_options: JSON.stringify({
	            		'measures':this.pivot_options.measures,
	            		'filter':this.graph_view.dataset.domain,
	            		'col':this._build_field_list(this.pivot.cols.groupby),
	            		'row':this._build_field_list(this.pivot.rows.groupby)}),
	            	title:this.title
	            },
	            complete: openerp.web.unblockUI,
	            error: c.rpc_error.bind(c)
	        });
	    },
	    
	    _build_field_list: function(fields){
	    	var list=[];
	    	for (var i in fields) {
	    		list.push(fields[i].string);
	    	}
	    	return list;
	    }
	    
	});
}

