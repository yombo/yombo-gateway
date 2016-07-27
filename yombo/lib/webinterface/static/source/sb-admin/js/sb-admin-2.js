$(function() {

    $('#side-menu').metisMenu();

});

//Loads the correct sidebar on window load,
//collapses the sidebar on window resize.
// Sets the min-height of #page-wrapper to window size
$(function() {
    $(window).bind("load resize", function() {
        var topOffset = 50;
        var width = (this.window.innerWidth > 0) ? this.window.innerWidth : this.screen.width;
        if (width < 768) {
            $('div.navbar-collapse').addClass('collapse');
            topOffset = 100; // 2-row-menu
        } else {
            $('div.navbar-collapse').removeClass('collapse');
        }

        var height = ((this.window.innerHeight > 0) ? this.window.innerHeight : this.screen.height) - 1;
        height = height - topOffset;
        if (height < 1) height = 1;
        if (height > topOffset) {
            $("#page-wrapper").css("min-height", (height) + "px");
        }
    });

    var url = window.location;
    // var element = $('ul.nav a').filter(function() {
    //     return this.href == url;
    // }).addClass('active').parent().parent().addClass('in').parent();
    var element = $('ul.nav a').filter(function() {
     return this.href == url;
    }).addClass('active').parent();

    while(true){
        if (element.is('li')){
            element = element.parent().addClass('in').parent();
        } else {
            break;
        }
    }

    handleSidebarToggler();
});

//Top Toggler
var handleSidebarToggler = function () {
	var body = $('body');

	// handle sidebar show/hide
	body.on('click', '.sidebar-toggler', function (e) {

		var sidebarMenuSubs = $('#sidebar .nav-second-level, #sidebar .nav-third-level');

		//collapse("toggle") した際にheightが「0」になるため、height style削除
		$("#sidebar-area .dropdown-collapse").parent("li").children("ul").css('height', '');

		$(".sidebar-search", $('.page-sidebar')).removeClass("open");
		if (body.hasClass("sidebar-closed")) {
			body.removeClass("sidebar-closed");
			sidebarMenuSubs.addClass('collapse');

			if ($.cookie) {
				$.cookie('sidebar-closed', '0');
			}
		} else {
			body.addClass("sidebar-closed");
			sidebarMenuSubs.removeClass('collapse');

			if ($.cookie) {
				$.cookie('sidebar-closed', '1');
			}
		}
		$(window).trigger('resize');
	});
};

//IE Checker
var isIE = function() {
	var undef,
		v = 3,
		div = document.createElement("div"),
		all = div.getElementsByTagName("i");
	while (
		div.innerHTML = "<!--[if gt IE " + (++v) + "]><i></i><![endif]-->",
		all[0]
	) {
		return v > 4 ? v : undef;
	}
}
