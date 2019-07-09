import {LiteEvent} from 'helper';
import { ShowDropdown } from 'Dropdown';
import slickgrid = require('slickgrid');
import { EL, bufferToHex } from 'helper';

export class GridCtrl {
	availableColSet = new Set<string>();
	visibleCols : string[] = [];
	colStyles : any = {};
	data : any[] = [];
	//rowHeight = 20;
	//headerHeight = 26;

	table : HTMLElement;
	thead : HTMLElement;
	tbody : HTMLElement;
	onItemClick = new LiteEvent<any>();

	constructor(root : HTMLElement, visibleCols : string[]) {
		var scrollContainer : HTMLDivElement;
		root.appendChild(this.table = EL("div", {"class":"GridCtrl"},
			//EL("div", {"class":"gridinnerDiv"},
				EL("div", {"class":"headouterDiv"}, 
					this.thead = EL("div", {"class":"thead"}),
				),
				scrollContainer = <HTMLDivElement>EL("div", {"class":"bodyouterDiv"}, 
					this.tbody = EL("div", {"class":"tbody"})
				),
			//)
		));
		scrollContainer.addEventListener("scroll", (e)=> {
			this.thead.style.marginLeft = (-scrollContainer.scrollLeft) + "px";
		});
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
		var width=0;
		names.forEach((name) => {
			if (!(name in this.colStyles)) this.colStyles[name] = { width: 100 };
			width += this.colStyles[name].width;
		})
		this.thead.innerHTML = "";
		this.thead.appendChild(this.buildRow(names, "th"));
		//this.thead.style.width = width+"px";
		//this.tbody.style.width = width+"px";
		this.setData(this.data, false);
	}
	toggleCol(name:string) {
		if (this.visibleCols.indexOf(name)===-1)
			this.setCols(this.visibleCols.concat([name]));
		else
			this.setCols(this.visibleCols.filter((x) => x != name));
	}
	getColStyle(index:number) {
		return this.colStyles[this.visibleCols[index]];
	}
	applyCellStyle(columnIndex:number, cell:HTMLDivElement) : number {
		var style = this.getColStyle(columnIndex);
		cell.style.width = style.width + "px";
		return style.width;
	}

	clearRows() {
		this.availableColSet = new Set(); //Set stores insertion order :-)
		this.tbody.innerHTML = "";
		this.data = [];
	}
	appendRow(o : any) {
		this.data.push(o);
		var keys = Object.keys(o);
		for (var i=0;i<keys.length;i++) if(!keys[i].startsWith("_")) this.availableColSet.add(keys[i]);

		var ar : string[] = [];
		for (var j=0; j<this.visibleCols.length; j++) {
			ar[j] = o[this.visibleCols[j]];
		}
		var row = this.buildRow(ar, "td");
		row.addEventListener("click", (e) => {
			this.onItemClick.trigger(o);
		});
		this.tbody.appendChild(row);
	}
	buildRow(array : string[], elType : string = "td") : HTMLDivElement {
		var row = document.createElement("div"); row.classList.add("tr");
		var x = 0;
		//row.style.height = this.rowHeight + "px";
		for (var i = 0; i<array.length; i++) {
			var el = <HTMLDivElement> document.createElement("div");
			el.className = elType;
			el.innerText = array[i];
			el.style.left = x + "px";
			x += this.applyCellStyle(i, el);
			row.appendChild(el);
		}
		row.style.width = x + "px";
		return row;
	}
	setData(data : any[], scrollToTop : boolean) {
		this.clearRows();
		data.forEach((row) => this.appendRow(row));
	}
	resizeCanvas() {}

}

export class SlickGridCtrl extends slickgrid.Grid<any>{
	availableColSet = new Set<string>();
	onItemClick = new LiteEvent<any>();

	constructor(root : HTMLElement, visibleCols : string[]) {
		super(root, [], visibleCols.map((name) => ({ id: name, name: name, field: name })), {
		});
	}

	clearRows() {
		this.setData([], true);
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
		this.setData(packets.map((packet) => {
			var fields = packet.f;

			var o : any = { 'time': packet.t, '_packetData': packet };
			for(var j = 0; j<fields.length;j++) {
				var [proto, field, display, raw] = fields[j];
				//this.availableColSet.add(proto + "." + field);
				o[proto + "." + field] = display;
				o['_raw.' + proto + "." + field] = raw;
			}
			return o;
		}), true);
	}
}