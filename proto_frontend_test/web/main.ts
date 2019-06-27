
/*
class Field {
	bytes : Uint8Array;
	name : string;
	description : string;
	value : string;
	valueDescription : string;
	children : Packet[] | Field[];
}
class Packet {
	bytes : Uint8Array;
	name : string;
	description : string;
	fields : Field[];
}
class PacketStream {
	packets : Packet[];
}

let streams : PacketStream[] = [];
*/

import * as rpc from './rpc';
import { decode as cbor_decode } from 'cbor/cbor';
import GoldenLayout from 'golden-layout';
import $ from 'jquery';
import { generateTypeEditorByName } from './TypeEditor';
import { PacketGrid } from 'PacketGrid';
import { FileList } from 'FileList';

var layout : GoldenLayout;

var layoutConfig = {
	settings:{
		// hasHeaders: true,
		// constrainDragToContainer: true,
		// reorderEnabled: true,
		// selectionEnabled: false,
		// popoutWholeStack: false,
		// blockedPopoutsThrowError: true,
		// closePopoutsOnUnload: true,
		// showPopoutIcon: true,
		// showMaximiseIcon: true,
		// showCloseIcon: true
	},
	dimensions: {
		// borderWidth: 5,
		// minItemHeight: 10,
		// minItemWidth: 10,
		// headerHeight: 20,
		// dragProxyWidth: 300,
		// dragProxyHeight: 200
	},
	labels: {
		// close: 'close',
		// maximise: 'maximise',
		// minimise: 'minimise',
		// popout: 'open in new window'
	},
	content: [{
		type: 'column',
		content: [
			{
			type:'component',
			componentName: 'filelist',
			componentState: { dir: 'scripts/' },
			isClosable: false
			},
			{
			type:'component',
			title:'scripts/hallo.py',
			componentName: 'editor',
			componentState: { filename: 'scripts/hallo.py' },
			},
		  {
			type:'component',
			componentName: 'packetlist',
			componentState: { filename: '../test3.pcap' }
			},
		  {
			type:'component',
			componentName: 'hexdump',
			componentState: { filename: '../test3.pcap' }
			}
		]
	  }]
};

var editor : monaco.editor.IStandaloneCodeEditor;
var pg : PacketGrid;

export function openEditor(filename : string) {
	layout.root.addChild({
		type:'component',
		title: filename,
		componentName: 'editor',
		componentState: { filename: filename },
	})
}
export function startApp() {
	
	if ("layoutConfig" in window.localStorage) {
		layoutConfig = JSON.parse(window.localStorage["layoutConfig"]);
	}
	layout = new GoldenLayout( layoutConfig );
	layout.on( 'stateChanged', function(){
		var state = JSON.stringify( layout.toConfig() );
		localStorage.setItem( 'layoutConfig', state );
	});
	
	
	layout.registerComponent( 'editor', function( container:any, state:any ){
		editor = monaco.editor.create(container.getElement()[0]!!, {
			value: [
				'# eile mit weile'
			].join('\n'),
			language: 'python',
			theme: "vs-dark",
		});
		editor.getModel()!!.updateOptions({insertSpaces:false});

		rpc.exec('getscript', {'file':state.filename}).then(function(result) {
			editor.setValue(<string>result);
		})

		function saveScript() {
			console.log("Save...");
			return rpc.exec('putscript', {'file':state.filename, 'content':editor.getValue()})
			.then(function() {
				console.log("Saved");
			});
		}
		
		
		editor.onKeyDown(function(e) {
			console.log(e);
			if (e.code == "Enter" && (e.metaKey || e.ctrlKey)) {
				saveScript().then(function() {
					return rpc.exec('parse_pcap_file', {'pcap_filename':"../test3.pcap", 'script_filename':state.filename})
				})
				.then(function(response : any) {
					var returnCode = response[0], enc_data = response[1], stderr = response[2];
					if (returnCode != 0) {
						var errstring = new TextDecoder("utf-8").decode(enc_data);
						alert("Error: " + returnCode + "\n" + errstring);
					}

					//alert("OK");
					document.getElementById("hexdump")!!.innerText = hexdump(enc_data, 16);
					var data : any = cbor_decode(typedArrayToBuffer(enc_data));
					pg.displayPackets(data.packets);
				});
				e.preventDefault();
				e.stopPropagation();
			}
			if (e.code == "KeyS" && (e.metaKey || e.ctrlKey)) {
				saveScript();
				e.preventDefault();
				e.stopPropagation();
			}
		})
		container.on("resize", function() {
			editor.layout();
		})
	});
	layout.registerComponent( 'packetlist', function( container:any, state:any ){
		var table = <HTMLTableElement> $("<table></table>").appendTo(container.getElement())[0];
		pg = new PacketGrid(table, ["time", "IP.src", "IP.dst"]);
	});
	layout.registerComponent( 'filelist', function( container:any, state:any ){
		var table = <HTMLTableElement> $("<table></table>").appendTo(container.getElement())[0];
		var fl = new FileList(table, state.dir);
		fl.onItemClick.on(function(item) {
			var filename = fl.dir + item.name;

		});
	});

	layout.registerComponent( 'hexdump', function( container:any, state:any ){
		container.getElement().html( '<div id="hexdump" class="hexdump"></div>');
	});

	rpc.init(function() {
		rpc.exec("login", {"name":"aaa"});
		layout.init();
	})

}
function typedArrayToBuffer(array: Uint8Array): ArrayBuffer {
    return array.buffer.slice(array.byteOffset, array.byteLength + array.byteOffset)
}
function bufferToHex (buffer : Uint8Array | ArrayBuffer) {
    return Array
        .from (new Uint8Array (buffer))
        .map (b => b.toString (16).padStart (2, "0"))
        .join ("");
}
function hexdump(buffer : Uint8Array, blockSize : number) {
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
