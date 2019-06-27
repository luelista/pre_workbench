import {LiteEvent} from 'helper';
import { ShowDropdown } from 'Dropdown';

export class GridCtrl {
	availableColSet = new Set<string>();
	visibleCols : string[] = [];
	table : HTMLTableElement;
	thead : HTMLTableSectionElement;
	tbody : HTMLTableSectionElement;
	onItemClick = new LiteEvent<any>();

	constructor(root : HTMLTableElement, visibleCols : string[]) {
		this.table = root;
		this.table.classList.add("GridCtrl");
		root.innerHTML="";
		this.thead = document.createElement("thead"); root.appendChild(this.thead);
		this.tbody = document.createElement("tbody"); root.appendChild(this.tbody);
		this.thead.addEventListener("contextmenu", (e)=> {
			var cm : any = {};
			this.availableColSet.forEach((c) => cm[c] = () => this.toggleCol(c));
			ShowDropdown(e, cm);
			e.preventDefault(); return false;
		})
		this.setCols(visibleCols);
	}

	setCols(names : string[]) {
		this.visibleCols = names;
		this.thead.innerHTML = "";
		this.thead.appendChild(GridCtrl.buildRow(names, "th"));
	}
	toggleCol(name:string) {
		if (this.visibleCols.indexOf(name)===-1)
			this.setCols(this.visibleCols.concat([name]));
		else
			this.setCols(this.visibleCols.filter((x) => x != name));
	}

	clearRows() {
		this.availableColSet = new Set(); //Set stores insertion order :-)
		this.tbody.innerHTML = "";
	}
	appendRow(o : any) {
		var keys = Object.keys(o);
		for (var i=0;i<keys.length;i++) this.availableColSet.add(keys[i]);

		var ar : string[] = [];
		for (var j=0; j<this.visibleCols.length; j++) {
			ar[j] = o[this.visibleCols[j]];
		}
		var row = GridCtrl.buildRow(ar, "td");
		row.addEventListener("click", (e) => {
			this.onItemClick.trigger(o);
		});
		this.tbody.appendChild(row);
	}
	static buildRow(array : string[], elType : string = "td") : HTMLTableRowElement {
		var row = document.createElement("tr");
		for (var i = 0; i<array.length; i++) {
			var el = document.createElement(elType);
			el.innerText = array[i];
			row.appendChild(el);
		}
		return row;
	}

}
export class PacketGrid extends GridCtrl {
	displayPackets(packets : any[]) {
		this.clearRows();

		for(var i=0;i<packets.length;i++) {
			var fields = packets[i].f;

			var o : any = { 'time': packets[i].t };
			for(var j = 0; j<fields.length;j++) {
				var [proto, field, display, raw] = fields[j];
				//this.availableColSet.add(proto + "." + field);
				o[proto + "." + field] = display;
			}
			this.appendRow(o);
		}
	}
}