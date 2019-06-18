$(window).load(function () {
    if (window.location.href.indexOf("in_iframe") > -1) {
        $('html').addClass('in_iframe');
        $('#oe_main_menu_navbar').css('display', "none")
        $('#wrapwrap header').css('display', "none")
        $('#wrapwrap footer').css('display', "none")
    }
});