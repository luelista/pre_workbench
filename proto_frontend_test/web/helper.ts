
export class LiteEvent<T>  {
	private handlers: { (data?: T): void; }[] = [];

	public on(handler: { (data?: T): void }) : void {
		this.handlers.push(handler);
	}

	public off(handler: { (data?: T): void }) : void {
		this.handlers = this.handlers.filter(h => h !== handler);
	}

	public trigger(data?: T) {
		this.handlers.slice(0).forEach(h => h(data));
	}
}

export function typedArrayToBuffer(array: Uint8Array): ArrayBuffer {
	return array.buffer.slice(array.byteOffset, array.byteLength + array.byteOffset)
}
export function bufferToHex (buffer : Uint8Array | ArrayBuffer, delim : string = "") {
	return Array
		.from (new Uint8Array (buffer))
		.map (b => b.toString (16).padStart (2, "0"))
		.join (delim);
}
export function EL(name:string, attrs:any, ...children:(string|HTMLElement)[]) : HTMLElement {
	var el = document.createElement(name);
	if (attrs) for(var key in attrs)
		if (key.startsWith("on")) el.addEventListener(key.substr(2), attrs[key], false);
		else el.setAttribute(key, attrs[key]);
	
	for(var i=0;i<children.length;i++){
		if (children[i] instanceof HTMLElement) el.appendChild(<HTMLElement>children[i]);
		else el.appendChild(document.createTextNode(""+children[i]));
	}
	return el;
}



export function flattenPacket(packet:any) {
	var out : any = { 'time': packet[0].time, '_packetData': packet };
	iteratePacket(packet, function(hash : any, level : number) {
		out[hash.name] = hash.show;
		out['_raw.'+hash.name] = hash.value;
	});
	return out;
}
export function iteratePacket(packet:any, cb:Function, startDepth:number = 0) {
	let [ hash, children ] = packet;
	cb(hash, startDepth);
	for(var i = 0; i < children.length; i++)
		iteratePacket(children[i], cb, startDepth+1);
}
export function getPacketLength(packet:any) {
	if (packet[0]['_length']) return packet[0]['_length'];
	var len = 0;
	iteratePacket(packet, function(hash : any, level : number) {
		if (hash.offset && hash.value) {
			var end = hash.offset + hash.value.len;
			if (end > len) len = end;
		}
	});
	packet[0]['_length'] = len;
	return len;
}
