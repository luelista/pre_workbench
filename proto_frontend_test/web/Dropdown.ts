
import $ from 'jquery';

export function ShowDropdown(event : MouseEvent, menuItems : any[]) {
		console.log(event)
		var menu = $("<div class='raumsel'></div>");
		menuItems.forEach(item => {
				var el = $("<div>"+item.text+"</div>").appendTo(menu);
				if (item.action)
					el.click(item.action);
				else
					el.addClass("disabled");
						
		})
		$(document.body).append(menu);
		var left = event.pageX;
		if (left + menu[0].clientWidth > window.innerWidth) left = window.innerWidth - menu[0].clientWidth ;
		var maxheight = window.innerHeight - event.pageY - 30;
		menu.css({ top: event.pageY + "px", left: left + "px", maxHeight: maxheight + "px" });
		setTimeout(function() {
			$(document).one("click", function(e) {
				menu.remove(); e.preventDefault();
			})
			$(document).one("contextmenu", function(e) {
				menu.remove(); e.preventDefault();
			})
		},1)
}


