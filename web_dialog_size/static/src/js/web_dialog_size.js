openerp.web_dialog_size= function (instance) {
	
	dialog_state=[];
	
	

    instance.web.Dialog =  instance.web.Dialog.extend({
    	
    	init_dialog: function () {
            var self = this;
            this._super();
            self.$dialog_box.find('.dialog_button_restore').addClass('dialog_button_hide');
            if (this.dialog_options.size !== 'large'){
                self.$dialog_box.find('.dialog_button_extend').addClass('dialog_button_hide');
            }
            else{
                self.$dialog_box.find('.dialog_button_extend').on('click', self._extending);
                self.$dialog_box.find('.dialog_button_restore').on('click', self._restore);
            }

            this._apply_custom_options((this.getParent().action_context!=undefined && this.getParent().action_context!=null)?this.getParent().action_context:null);
        },

        _extending: function() {
            var self = this;
            $(this).parents('.modal-dialog').addClass('dialog_full_screen');
            $(this).addClass('dialog_button_hide');

            $(this).parents('.modal-dialog').find('.dialog_button_restore').removeClass('dialog_button_hide')
        },

        _restore: function() {
            var self = this;
            $(this).parents('.modal-dialog').removeClass('dialog_full_screen');
            $(this).addClass('dialog_button_hide');

            $(this).parents('.modal-dialog').find('.dialog_button_extend').removeClass('dialog_button_hide')
        },
        
        _apply_custom_options: function(options) {
        	if((options!=null && options.context!=undefined && options.context!=null && options.context.dialog_full_size)) {
        		dialog_state[options.view_id]=true;
        	}
        	if(options!=null && options.view_id!=null && dialog_state[options.view_id]!=undefined && dialog_state[options.view_id]) {
        		this.$dialog_box.find('.modal-dialog').addClass('dialog_full_screen');
           	 	this.$dialog_box.find('.dialog_button_extend').addClass('dialog_button_hide');
           	 	this.$dialog_box.find('.dialog_button_restore').removeClass('dialog_button_hide');
        	}
        }

    });
    
    instance.web.ActionManager =  instance.web.ActionManager.extend({
    	
    	action_context:null,
    	
    	ir_actions_act_window: function (action, options) {
            var self = this;
            console.log(action);
            this.action_context=action;
            return this._super(action, options);
        }

    });

};

