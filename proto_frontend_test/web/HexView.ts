
export class HexView {
	root : HTMLDivElement;
	constructor(parent:HTMLElement) {
		this.root = <HTMLDivElement> document.createElement("div");
		parent.appendChild(this.root);
		this.root.className="hexdump";
	}
	showHex(buf : Uint8Array) {
		this.root.innerText = hexdump(buf, 16);
	}
	showPacketHex(fields : any[]) {
		var items : any[]= [];
		var colors = [ ["#440000", "#880000"], ["#004400","#008800"], ["#000044","#000088"], ["#444400","#888800"], ["#004444","#008888"], ["#440044","#880088"] ];
		var colorIdx = -1, subcoloridx = 0;
		var lastProto = "";
		fields.forEach((f) => {
			var [proto, field, display, raw] = f;
			if (lastProto != proto) {
				colorIdx = (colorIdx+1) % colors.length;
				lastProto = proto;
			}
			subcoloridx = (subcoloridx+1) % 2;
			(<Uint8Array>raw).forEach((byte) => {
				items.push({ byte: byte, color: colors[colorIdx][subcoloridx], title: proto+"."+field+" = "+display });
			})
		})
		this.root.innerHTML = hexdump2(items, 16);
	}
}
export function hexdump(buffer : Uint8Array, blockSize : number) {
    blockSize = blockSize || 16;
    var lines = [];
    var hex = "0123456789ABCDEF";
    for (var b = 0; b < buffer.length; b += blockSize) {
        var thisblocksize = Math.min(blockSize, buffer.length - b);
		var addr = ("0000" + b.toString(16)).slice(-4);
		var codes = "", chars="";
		for(var i = 0; i < thisblocksize; i++) {
			var code = buffer[b + i];
			codes += " " + hex[(0xF0 & code) >> 4] + hex[0x0F & code];
			chars += (code > 0x20 && code < 0x80) ? String.fromCharCode(code) : ".";
		}
        codes += "   ".repeat(blockSize - thisblocksize);
        chars +=  " ".repeat(blockSize - thisblocksize);
        lines.push(addr + " " + codes + "  " + chars);
    }
    return lines.join("\n");
}
export function hexdump2(buffer : any[], blockSize : number) {
    blockSize = blockSize || 16;
    var lines = [];
    var hex = "0123456789ABCDEF";
    for (var b = 0; b < buffer.length; b += blockSize) {
        var thisblocksize = Math.min(blockSize, buffer.length - b);
		var addr = ("0000" + b.toString(16)).slice(-4);
		var codes = "", chars="";
		for(var i = 0; i < thisblocksize; i++) {
			var code = buffer[b + i].byte;
			codes += "<span style='background:"+buffer[b+i].color+";color:white' title='"+buffer[b+i].title.replace(/'/g,"&apos;")+"'> " + hex[(0xF0 & code) >> 4] + hex[0x0F & code] + "</span>";
			chars += (code > 0x20 && code < 0x80 && code != 60) ? String.fromCharCode(code) : ".";
		}
        codes += "   ".repeat(blockSize - thisblocksize);
        chars +=  " ".repeat(blockSize - thisblocksize);
        lines.push(addr + " " + codes + "  " + chars);
    }
    return lines.join("\n");
}
