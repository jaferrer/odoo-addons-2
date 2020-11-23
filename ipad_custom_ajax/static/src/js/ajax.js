odoo.define('ipad.custom.ajax', function (require) {
    "use strict";

    let web_ajax = require('web.ajax');
    let original_get_file = web_ajax.get_file;
    web_ajax.get_file = function (options) {
        var token = new Date().getTime();

        // iOS devices doesn't allow iframe use the way we do it,
        // opening a new window seems the best way to workaround
        if (navigator.userAgent.match(/(iPod|iPhone|iPad|Macintosh)/)) {
            var params = _.extend({}, options.data || {}, {token: token});
            var url = options.session.url(options.url, params);
            if (options.complete) {
                options.complete();
            }

            return window.open(url);
        }
        return original_get_file(options)
    };
})