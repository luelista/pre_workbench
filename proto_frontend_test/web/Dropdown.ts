
import $ from 'jquery';

export function ShowDropdown(event : MouseEvent, menuItems : any) {
		console.log(event)
		var menu = $("<div class='raumsel'></div>");
		menu.css({ top: event.pageY + "px", left: event.pageX + "px" });
		for(var k in menuItems) {
				var item = $("<div>"+k+"</div>").appendTo(menu);
				if (menuItems[k] === false)
						item.addClass("disabled");
					else
						item.click(menuItems[k]);
		}
		$(document.body).append(menu);
		setTimeout(function() {
			$(document).one("click", function(e) {
				menu.remove(); e.preventDefault();
			})
			$(document).one("contextmenu", function(e) {
				menu.remove(); e.preventDefault();
			})
		},1)
}


