openerp.document_scanner = function (instance) {
    _t = instance.web._t;
    instance.web.Sidebar.include({

	    start: function() {
	        this._super();
	        self=this;
	        this.$el.on('click','.oe_sidebar_scan_attachment_select', function(event) {
	        	ids=self.getParent().get_selected_ids()
	        	var context = {
	                    active_id: ids[0],
	                    active_ids: ids,
	                    active_model: self.getParent().dataset.model
	             };
            	new instance.web.Model('ir.attachment')
	            .call('scan',[context])
	            .then(function(data){
	            	
	                if(data && data.error!=undefined) {
	                	console.log(data);
	                	alert("Document ne s'est pas enregistré \nMessage"+data.error);
	                } else {
	                	self.do_notify(_t("Scanning information"),"Le Document s'est enregistré correctement sous : "+data.file);
	                	self.do_attachement_update(self.getParent().dataset, self.getParent().get_selected_ids()[0],false);
	                }
	            });
	        });
	    }
    });
};
