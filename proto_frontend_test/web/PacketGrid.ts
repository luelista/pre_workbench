import {GridCtrl} from 'GridCtrl';
import { flattenPacket } from 'helper';


export class PacketGrid extends GridCtrl {
	displayPackets(packets : any[]) {
		this.setData(packets.map(flattenPacket), true);
	}
}
