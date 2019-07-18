import {LiteEvent} from 'helper';
import { ShowDropdown } from 'Dropdown';
import slickgrid = require('slickgrid');
import { EL, bufferToHex } from 'helper';
class ColInfo {
	key : string;
	expression : string = "";
	title : string;
	width : number = 150;
	visible : boolean = false;
	available : boolean = true;
	constructor(title:string,key:string){
		this.key=key; this.title=title;
	}
}
export class GridCtrl {
	availableColSet = new Set<string>(); //Set stores insertion order :-)
	visibleCols : ColInfo[] = [];
	cols : ColInfo[] = [];
	colsMap : {[key:string] : ColInfo} = {};
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
			var cm : any[] = [];
			this.cols.filter((c) => c.visible || c.available).forEach((c) => cm.push({text:c.title,action:() => this.toggleCol(c)}))
			cm.push({text:"-"});
			this.availableColSet.forEach((c) => c in this.colsMap || cm.push({text:c, action: () => this.addCol(c, c)}));
			ShowDropdown(e, cm);
			e.preventDefault(); return false;
		})
		this.setCols(visibleCols);
	}

	fillHeaderRow(tr : HTMLElement) : HTMLElement {
		for (var i = 0; i<this.visibleCols.length; i++) {
			var el = <HTMLDivElement> EL("div", {"class":"th"}, this.visibleCols[i].title);
			tr.appendChild(el);
		}
		this.applyCellStylesOnRow(tr);
		return tr;
	}
	addCol(title:string,key:string){
		if (key in this.colsMap) {
			if (!this.colsMap[key].visible) this.colsMap[key].visible=true;
		} else {
			var info = new ColInfo(title,key);
			info.visible=true;
			this.cols.push(info);
		}
		this.updateCols();
	}
	setCols(names : string[]) {
		this.cols.forEach(col => col.visible=false);
		names.forEach(name => {
			this.addCol(name, name);
		})
	}

	updateCols() {
		this.visibleCols = this.cols.filter((c) => c.visible);
		this.colsMap = {};
		this.cols.forEach(col => this.colsMap[col.key] = col);
		this.thead.innerHTML = "";
		this.thead.appendChild(this.fillHeaderRow(EL("div",{"class":"tr"})));
		for(var i =0; i < this.data.length; i++) {
			this.fillRowWithData(this.data[i]['_tr'], this.data[i]);
		}
	}
	toggleCol(col:ColInfo) {
		console.log(col,this)
		col.visible = !col.visible;
		this.updateCols();
	}
	getColStyle(index:number) {
		return this.visibleCols[index];
	}
	applyCellStyle(columnIndex:number, cell:HTMLDivElement) : number {
		var style = this.getColStyle(columnIndex);
		cell.style.width = style.width + "px";
		return style.width;
	}
	applyCellStylesOnRow(tr : HTMLDivElement) {
		var x = 0;
		for(var j =0; j < this.visibleCols.length; j++) {
			tr.children[j].style.left = x + "px";
			x += this.applyCellStyle(j, tr.children[j]);
		}
		tr.style.width = x + "px";
	}
	applyCellStyles() {
		this.applyCellStylesOnRow(this.thead.children[0]);
		for(var i =0; i < this.data.length; i++) {
			this.applyCellStylesOnRow(this.data[i]['_tr']);
		}
	}

	clearRows() {
		this.availableColSet = new Set();
		this.tbody.innerHTML = "";
		this.data = [];
	}
	appendRow(o : any, container : HTMLDivElement = this.tbody) {
		this.data.push(o);
		var keys = Object.keys(o);
		for (var i=0;i<keys.length;i++) if(!keys[i].startsWith("_")) this.availableColSet.add(keys[i]);

		var ar : string[] = [];
		for (var j=0; j<this.visibleCols.length; j++) {
			ar[j] = o[this.visibleCols[j].key];
		}
		var row = EL("div", {"class":"tr"});
		o['_tr'] = row;
		this.fillRowWithData(row, o);
		row.addEventListener("click", (e) => {
			this.onRowClick(o);
		});
		container.appendChild(row);
	}
	onRowClick(o : any) {
		this.onItemClick.trigger(o);
	}
	fillRowWithData(tr : HTMLDivElement, o : any) {
		tr.innerHTML = "";
		for (var i = 0; i<this.visibleCols.length; i++) {
			var colKey = this.visibleCols[i].key;
			var el = <HTMLDivElement> EL("div", {"class":"td","data-col-key":colKey});
			this.formatValue(o[colKey], el);
			tr.appendChild(el);
		}
		this.applyCellStylesOnRow(tr);
	}
	formatValue(value : any, into: HTMLDivElement) {
		if (typeof value == "undefined") {
			into.style.color = "#777";
			into.innerText = "(undef.)";
		} else if (value === "null") {
			into.style.color = "#777";
			into.innerText = "(null)";
		} else if (typeof value == "number") {
			into.style.textAlign = "right";
			into.innerText = ""+value;
		} else if (value instanceof Uint8Array) {
			into.innerText = bufferToHex(value, " ");
		} else {
			into.innerText = ""+value;
		}
	}
	setData(data : any[], scrollToTop : boolean) {
		console.log("grid setData",data)
		this.clearRows();
		data.forEach((row) => this.appendRow(row));
	}
	resizeCanvas() {}

}

export class TreeCtrl extends GridCtrl {
	expandStates : any = {};

	setTreeData(treeData : [any,any]) {
		this.clearRows();
		this.recursiveAdd(treeData, this.tbody, 0, true);
	}

	fillRowWithData(tr : HTMLDivElement, o : any) {
		super.fillRowWithData(tr, o);
		var firstCol = tr.children[0];
		firstCol.style.paddingLeft=o['_level']*15 + "px";
		firstCol.addEventListener("click", () => {
			var newState = !$(tr.nextSibling).is(":visible");
			if (newState) this.onBeforeExpand(tr.parentNode, o);
			$(tr.nextSibling).toggle(newState);
			this.expandStates [o['_stateId']] = newState;
			tr.parentNode.classList.remove("collapsed");tr.parentNode.classList.remove("expanded");
			tr.parentNode.classList.add(newState?"expanded":"collapsed");
		});
	}

	onBeforeExpand(treeRow : HTMLDivElement, o : any) {
	}

	onPrepareData(hash:any) {
	}

	recursiveAdd(packetData : [any,any], parentContainer : HTMLDivElement, level : number, defaultExpanded : boolean) {
		var [hash, children] = packetData;
		hash['_level'] = level;
		this.onPrepareData(hash);

		var state = "empty", expanded = defaultExpanded;
		if (children.length > 0 || hash['_lazyLoadChildren']) {
			state = "has-children ";
			if (typeof this.expandStates[hash['_stateId']] === "boolean") expanded=this.expandStates[hash['_stateId']];
			state += expanded?"expanded":"collapsed";
		}
		var rowContainer = <HTMLDivElement>EL("div", {"class":"treeRow "+state});
		parentContainer.appendChild(rowContainer);
		this.appendRow(hash, rowContainer);
		
		var childContainer = EL("div", {"class":"treeChildren"});
		rowContainer.appendChild(childContainer);
		if (!expanded) $(childContainer).hide();
		else this.onBeforeExpand(rowContainer, hash);

		for(var i = 0; i < children.length; i++)
			this.recursiveAdd(children[i], childContainer, level+1, defaultExpanded);
	}

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
