odoo.define('web.fieldsketch', function (require) {
   "use strict";
   	
   var core = require('web.core');
   var utils = require('web.utils');
   var _t = core._t;
   var QWeb = core.qweb;

    var FieldSketch = core.form_widget_registry.get("image").extend({
	    template: 'FieldSketch',
	    placeholder: "/web/static/src/img/placeholder.png",
	    currentPicture:null,
	    effective_readonly:true,

	    init: function(field_manager, node) {

	    	this._super(field_manager, node);
	    	this.useFileAPI=false;
	    	var self = this;
	        this.fileupload_id = _.uniqueId('oe_fileupload');
	        this.canvas_id=_.uniqueId('simple_sketch')
	        this.imgpreview_id=_.uniqueId('imgpreview')
            $(window).on(this.fileupload_id, function() {
                var args = [].slice.call(arguments).slice(1);
                self.on_file_uploaded_and_valid.apply(self, args);
            });
	    },
	    
	    initialize_content: function() {
	    	this._super.apply(this, arguments);
	        this.$el.find('.oe_form_binary_file_cancel').click(this.on_cancel);
	        this.$el.find('.oe_form_binary_file_edit').click(this.on_edit);
	    },
	    
	    render_value: function() {
	        var self = this;
	        var url;
	        console.log(this.get('value'));
	        if (this.get('value') && !utils.is_bin_size(this.get('value'))) {
	            url = 'data:image/png;base64,' + this.get('value');
	        } else {
	            var id = JSON.stringify(this.view.datarecord.id || null);
	            var field = this.name;
	            if (this.options.preview_image)
	                field = this.options.preview_image;
	            url = this.session.url('/web/binary/image', {
	                                        model: this.view.dataset.model,
	                                        id: id,
	                                        field: field,
	                                        t: (new Date().getTime()),
	            });
	        }
	        var $img = $(QWeb.render("FieldSketch-img", { widget: this, url: url }));
	        $($img).click(function(e) {
	            if(self.view.get("actual_mode") == "view") {
	                var $button = $(".oe_form_button_edit");
	                $button.openerpBounce();
	                e.stopPropagation();
	            }
	        });
	        this.$el.find('> img').remove();
	        this.$el.find('> canvas').remove();
	        this.$el.prepend($img);
	        $img.load(function() {
	            if (! self.options.size)
	                return;
	            var width=self.options.size[0];
	            var height=self.options.size[1];
	            if ((self.options.size[0]).toString().indexOf("%")>=0) {
	            	width=self.$el.parent().width()*(self.options.size[0].replace("%","")/100);
	            }
	            if ((self.options.size[1]).toString().indexOf("%")>=0) {
	            	height=self.$el.parent().height()*(self.options.size[1].replace("%","")/100);
	            }
	            self.$el.find('> img').css("width", "" + width);
	            self.$el.find('> img').css("height", "" + height);
	            self.$el.find('> canvas').attr("width", "" + width);
	            self.$el.find('> canvas').attr("height", "" + height);
	        });
	        $img.on('error', function() {
	            $img.attr('src', self.placeholder);
	            self.do_warn(_t("Image"), _t("Could not display the selected image."));
	        });
	        
	    	if (!self.get("effective_readonly")) {
	    		if (self.options!=undefined) {
	    			if(self.options.size!=undefined){
	    				self.$el.find('#'+this.canvas_id).width(self.options.size[0]);
	    				self.$el.find('#'+this.canvas_id).height(self.options.size[1]);
	    			}
	    		}
	    	}
	    	this.currentPicture=url;
	    },
	    
	    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
	    	this.$el.find('.oe_form_binary_file_cancel').css("display","none");
	    	this.internal_set_value(file_base64);
	        this.binary_value = true;
	        this.set_filename(name);
	    },
	    on_clear: function() {
	    	var bool=false;
	    	if(this.currentPicture!=this.placeholder){
	    		bool=confirm("Are you sure to delete the sketch?");
	    	}
	    	if(bool) {
		        this._super.apply(this, arguments);
		        this.render_value();
		        this.set_filename('');
	    	}
	    },
	    
	    on_cancel: function() {
	        this.render_value();
	        this.$el.find('.oe_form_binary_file_edit').css("display","");
	        this.$el.find('.oe_form_binary_file_clear').css("display","");
	        this.$el.find('.oe_form_binary_file_cancel').css("display","none");
	    },
	    
	    on_edit: function() {
	    	var self=this;
	    	var bool=true;
	    	if(this.currentPicture!=this.placeholder){
	    		bool=confirm("Are you sure to modify the sketch?");
	    	}
	    	if(bool) {
		    	this.$el.find('.oe_form_binary_file_edit').css("display","none");
		        this.$el.find('.oe_form_binary_file_clear').css("display","none");
		        this.$el.find('.oe_form_binary_file_cancel').css("display","");
		        console.log('#'+this.canvas_id);
		        this.$el.find('#'+this.canvas_id).css("display","");
		    	this.$el.find('#'+this.imgpreview_id).css("display","none");
		    	this.$el.find('#'+this.canvas_id).sketch();
		    	this.$el.find('#'+this.canvas_id).on({
		    		mouseup:function(){
		    			self.on_valid_sketch();
		    		}
		    	});
		    	
		    	this.$el.find('#'+this.canvas_id).on("touchend",function(){
		    			self.on_valid_sketch();
		    		});
	    	} else {
	    		this.on_cancel();
	    	}
	    },
	    
	    dataURItoBlob: function (dataURI) {
	        // convert base64 to raw binary data held in a string
	        // doesn't handle URLEncoded DataURIs

	        var byteString;
	        if (dataURI.split(',')[0].indexOf('base64') >= 0) {
	            byteString = atob(dataURI.split(',')[1]);
	        } else {
	            byteString = unescape(dataURI.split(',')[1]);
	        }

	        // separate out the mime component
	        var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];

	        // write the bytes of the string to an ArrayBuffer
	        var ab = new ArrayBuffer(byteString.length);
	        var ia = new Uint8Array(ab);
	        for (var i = 0; i < byteString.length; i++) {
	            ia[i] = byteString.charCodeAt(i);
	        }

	        try {
	            return new Blob([ab], {type: mimeString});
	        } catch (e) {
	            var BlobBuilder = window.WebKitBlobBuilder || window.MozBlobBuilder;
	            var bb = new BlobBuilder();
	            bb.append(ab);
	            return bb.getBlob(mimeString);
	        }
	    },
	    
	    
	    on_valid_sketch:function() {
	    	var self=this;
	    	var data = new FormData();
	    	
	    	if(this.session.override_session){
	    		data.append('session_id', "");
	    	}
	    	data.append('callback',self.fileupload_id );
	    	if(document.getElementById(this.canvas_id).mozGetAsFile) {
	    		data.append('ufile', document.getElementById(this.canvas_id).mozGetAsFile('sign_'+(new Date()).getTime()+'.png'));
	    	} else {
	    		var imgtmp = document.getElementById(this.canvas_id).toDataURL('image/png', 0.7);
	            var blob = this.dataURItoBlob(imgtmp);
	            data.append('ufile',blob);
	    	}
	    	data.append('csrf_token',core.csrf_token);
	    	$.ajax({
	            type: 'POST',
	            url: this.fileupload_action || '/web/binary/upload',
	            data: data,
	            cache: false,
	            contentType: false,
	            processData: false,
	            success: function (data) {
	            	self.$el.find('#'+self.fileupload_id).html(data);
	            }
	        });
	    },
	    
	    set_value: function(value_){
	        var changed = value_ !== this.get_value();
	        // By default, on binary images read, the server returns the binary size
	        // This is possible that two images have the exact same size
	        // Therefore we trigger the change in case the image value hasn't changed
	        // So the image is re-rendered correctly
	        if (!changed){
	            this.trigger("change:value", this, {
	                oldValue: value_,
	                newValue: value_
	            });
	        }
	    }
	});

    core.form_widget_registry.add('sketch', FieldSketch);
	
});

