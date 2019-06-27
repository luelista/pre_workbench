
import * as rpc from './rpc';
import {GridCtrl} from 'PacketGrid';
import {ShowDropdown} from 'Dropdown';

export class FileList extends GridCtrl {
	dir : string = ""; //always ends with "/"

	constructor(root : HTMLTableElement, dir : string) {
		super(root,  ["name","size"]);
		this.loadDir(dir);
	}

	loadDir(dir : string) {
		if (dir != "" && !dir.endsWith("/")) dir += "/";
		this.dir=dir;
		rpc.exec("listdir", {"dir":dir}).then((dirlist) => {
			this.showList(dirlist);
		});
	}

	showList(entries : any[]) {
		this.clearRows();
		for(var i=0;i<entries.length;i++) {
			this.appendRow(entries[i]);
		}
	}
}