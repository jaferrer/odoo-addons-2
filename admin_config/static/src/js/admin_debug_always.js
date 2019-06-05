odoo.define('web.DebugManager_always', function (require) {
   "use strict";
   	
   var core = require('web.core');
   var utils = require('web.utils');
   var session = require('web.session');
   var debug=require('web.DebugManager');
   var SystrayMenu = require('web.SystrayMenu');
   var _t = core._t;
   var QWeb = core.qweb;

   var debug = $.deparam($.param.querystring()).debug !== undefined;
   if(!debug) {
	   var wid= require('web.Widget').extend({
		   start: function() {
	           if(session.uid === 1){
	        	   window.location.href="?debug=";
	           }
	       }
	   });
	   
	   SystrayMenu.Items.push(wid);
   
	   return wid;
   }
});
