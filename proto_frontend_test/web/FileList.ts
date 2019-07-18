
import * as rpc from './rpc';
import {TreeCtrl} from 'GridCtrl';
import {ShowDropdown} from 'Dropdown';

export class FileList extends TreeCtrl {
	dir : string = ""; //always ends with "/"

	constructor(root : HTMLElement, dir : string) {
		super(root,  ["name","size"]);
		this.loadDir(dir, this.tbody, 0);
	}

	loadDir(dir : string, container:HTMLElement, level : number) {
		if (dir != "" && !dir.endsWith("/")) dir += "/";
		this.dir=dir;
		rpc.exec("listdir", {"dir":dir}).then((dirlist) => {
			dirlist.forEach(element => {
				element._path = dir+element.name;
				this.recursiveAdd([element,[]], container, level, false);
			});
		});
	}
	onPrepareData(hash:any) {
		if (this.isDir(hash)) hash['_lazyLoadChildren']=true;
	}

	onRowClick(o : any) {
		if (!this.isDir(o))
			this.onItemClick.trigger(o);
	}

	isDir(o:any) {
		return (o["mode"] & 16384) == 16384;
	}

	onBeforeExpand(treeRow : HTMLDivElement, o : any) {
		console.log("onBeforeExpand",treeRow,o)
		if (!o['_lazyLoadChildren']) return;
		o['_lazyLoadChildren'] = false;
		this.loadDir(o['_path'], treeRow.children[1], o['_level']+1);
	}
}