(function() {
	
	
	
	new openerp.web.Model('load.css')
    .call('load_list_css')
    .then(function(data){
    	$('body').addClass("ndp-systemes");
    	for(i in data) {
    		$('head').prepend('<link rel="stylesheet" type="text/css" href="/portail_ndp/static/src/css/'+data[i]+'" />')
    	}
    });
})();

