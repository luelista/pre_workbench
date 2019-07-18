
import { EL, bufferToHex, iteratePacket } from 'helper';
import { TreeCtrl } from 'GridCtrl';


export function packetToTreeData(packet:any) {
	var out : any[] = []; //[{ 'time': packet[0].time, '_packetData': packet }];
	iteratePacket(packet, function(hash : any, level : number) {
		hash['_level'] = level;
		out.push(hash);
	});
	return out;
}
export class PacketDetailTree extends TreeCtrl {
	expandStates : any = {};

	constructor(root : HTMLElement) {
		super(root,  ['showname','show','pos','size','value']);
		//this.colsMap["name"].width = 200;
		this.colsMap["showname"].width = 300;
		this.colsMap["show"].width = 200;
		this.colsMap["pos"].width = 50;
		this.colsMap["size"].width = 50;
		this.colsMap["value"].width = 200;
		this.applyCellStyles();
	}

	onPrepareData(hash:any) {
		hash['_stateId'] = hash['name'];  //TODO abstract this away ???
	}

}
