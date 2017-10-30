(function() {

var instance = openerp;
	
	instance.web.form.FieldPhone = instance.web.form.FieldChar.extend({
	    template: 'FieldPhone',
	    initialize_content: function() {
	        this._super();
	    },
	    
	    render_value: function() {
	        if (!this.get("effective_readonly")) {
	            this._super();
	        } else {
	            this.$el.find('a')
	                    .attr('href', 'callto:' + this.get('value'))
	                    .text(this.get('value') || '');
	        }
	    }
	});	
	
	instance.web.form.widgets.add('phone', 'instance.web.form.FieldPhone');
	
})();

