import { iteratePacket } from 'helper';
class HexViewBuffer {
	data : Uint8Array = new Uint8Array();
	annotations : any[] = [];
	title : string = "";
}
/*
export class HexView2 {
	root : HTMLCanvasElement;
	buffers : HexViewBuffer[] = [];
	constructor(parent:HTMLElement) {
		this.root = <HTMLCanvasElement> document.createElement("canvas");
		parent.appendChild(this.root);
		
	}
	showHex(buf : Uint8Array) {
		this.buffers = [ { data: buf, annotations: [], title: "" } ];
	}
	showPacketHex(fields : any[]) {
		var items : any[]= [];
		var colors = [ ["#440000", "#880000"], ["#004400","#008800"], ["#000044","#000088"], ["#444400","#888800"], ["#004444","#008888"], ["#440044","#880088"] ];
		var colorIdx = -1, subcoloridx = 0;
		var lastProto = "";
		var destIdx = 0;
		fields.forEach((f) => {
			var [proto, field, display, raw] = f;
			if (lastProto != proto) {
				colorIdx = (colorIdx+1) % colors.length;
				lastProto = proto;
			}
			subcoloridx = (subcoloridx+1) % 2;
			this.data.set(raw, destIdx);
			this.annotations.push({ start: destIdx, length: raw.length,
				 color: colors[colorIdx][subcoloridx], title: field+" = "+display });

			this.annotations.push({ start: destIdx, length: raw.length,
				color: colors[colorIdx][subcoloridx], title: field+" = "+display });

			destIdx += raw.length;

		})
		this.root.innerHTML = hexdump2(items, 16);
	}
	draw() {

	}
	drawLine(yPos, ) {
		
	}
}*/
class AnnotatedBuffer {
	items : any[] = [];
	setByte(index:number, byteValue:number|undefined, annotation:any|undefined, style:any|undefined) {
		var item = this.items[index];
		console.log(index,byteValue)
		if (!item) {
			item = this.items[index] = { byte: byteValue, annotations: [], style: {} };
		} else if (byteValue !== undefined && item.byte !== undefined && item.byte !== byteValue) {
			console.warn("non-matching byte values at "+index,annotation,item,  byteValue,typeof byteValue, item.byte,typeof item.byte);
			return;
		} else if (byteValue !== undefined) {
			item.byte = byteValue;
		}
		if (annotation !== undefined) {
			item.annotations.push(annotation);
		}
		if (style !== undefined) {
			for (var k in style) item.style[k] = style[k];
		}
	}
	getStyle(index:number, styleName:string, defaultValue:any) {
		if (this.items[index] && styleName in this.items[index].style)
			return this.items[index].style[styleName];
		else
			return defaultValue;
	}
	getAnnotations(index:number, annotationProperty:string) {
		if (!this.items[index])
			return [];
		return this.items[index].annotations.map(function(el:any) { return el[annotationProperty]; }).filter(function(el:any){ return el !== undefined });
	}
}
function preparePacketHex(packet:any) {
	var buf = new AnnotatedBuffer();
	var colors = [ ["#440000", "#880000"], ["#004400","#008800"], ["#000044","#000088"], ["#444400","#888800"], ["#004444","#008888"], ["#440044","#880088"] ];
	var colorIdx = -1, subcoloridx = 0;
	var lastProto = "";
	iteratePacket(packet, function(hash:any, level:number) {
		//var [proto, field, display, raw] = f;
		if (level == 1) {
			colorIdx = (colorIdx+1) % colors.length;
		}
		subcoloridx = (subcoloridx+1) % 2;
		console.log(hash);
		if (typeof hash.offset==="number" && hash.value) {
			(<Uint8Array>hash.value).forEach((byte, i) => {
				buf.setByte(hash.offset + i, byte, {title: hash.name+" = "+hash.show },{color: colors[colorIdx][subcoloridx]});
			})
		} else if (hash.offset && hash.len) {
			for(var i = hash.offset; i < hash.offset+hash.len; i++)
				buf.setByte(i, undefined, {title: hash.name+" = "+hash.show },{color: colors[colorIdx][subcoloridx]});
		}
	});
	return buf;
}
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
	showPacketHex(packet : any) {
		var items = preparePacketHex(packet);
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
export function hexdump2(buffer : AnnotatedBuffer, blockSize : number) {
	console.log(buffer);
    blockSize = blockSize || 16;
    var lines = [];
    var hex = "0123456789ABCDEF";
    for (var b = 0; b < buffer.items.length; b += blockSize) {
        var thisblocksize = Math.min(blockSize, buffer.items.length - b);
		var addr = ("0000" + b.toString(16)).slice(-4);
		var codes = "", chars="";
		for(var i = 0; i < thisblocksize; i++) {
			console.log(b+i, buffer.items[b+i]);
			var code = buffer.items[b + i].byte;
			codes += "<span style='background:"+buffer.getStyle(b+i,"color","black")+";color:white' title='"+buffer.getAnnotations(b+i,"title").join("\n").replace(/'/g,"&apos;")+"'> " + hex[(0xF0 & code) >> 4] + hex[0x0F & code] + "</span>";
			chars += (code > 0x20 && code < 0x80 && code != 60) ? String.fromCharCode(code) : ".";
		}
        codes += "   ".repeat(blockSize - thisblocksize);
        chars +=  " ".repeat(blockSize - thisblocksize);
        lines.push(addr + " " + codes + "  " + chars);
    }
    return lines.join("\n");
}
