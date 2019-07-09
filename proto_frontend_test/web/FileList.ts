
import * as rpc from './rpc';
import {GridCtrl,SlickGridCtrl} from 'PacketGrid';
import {ShowDropdown} from 'Dropdown';

export class FileList extends GridCtrl {
	dir : string = ""; //always ends with "/"

	constructor(root : HTMLElement, dir : string) {
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
		this.setData(entries, true);
	}
}