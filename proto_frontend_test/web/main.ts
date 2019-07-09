
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
import { PacketGrid, GridCtrl } from 'PacketGrid';
import { FileList } from 'FileList';
import { typedArrayToBuffer, bufferToHex } from 'helper';
import { HexView } from 'HexView';

// fools
// https://github.com/xtermjs/xterm.js/issues/917
import * as xterm from 'xterm';
const TerminalConstructor = (xterm as any).default as (typeof xterm.Terminal);
import * as xtermFit from 'xterm/lib/addons/fit/fit';
TerminalConstructor.applyAddon(xtermFit);

var layout : GoldenLayout;

var layoutConfig = {
	settings:{
		// hasHeaders: true,
		// constrainDragToContainer: true,
		// reorderEnabled: true,
		selectionEnabled: true,
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
				componentName: 'packetdetail',
				componentState: {  },
				isClosable: false
			},
			{
				type:'component',
				componentName: 'hexdump',
				componentState: {  },
				isClosable: false
			},
			{
				type:'component',
				componentName: 'terminal',
				componentState: {  },
				id: 'terminal:log'
			}
		]
	  }]
};

var globalEditor : monaco.editor.IStandaloneCodeEditor;
var pg : PacketGrid;
var hexView : HexView;
var packetDetail : GridCtrl;

export function activateItem(id:string) : any {
	var items = layout.root.getItemsById(id);
	console.log("activateItem "+id,items);
	if (items.length > 0) {
		items[0].select();
		return items[0];
	} else {
		return null;
	}
}
export function openEditor(filename : string) /*: monaco.editor.IStandaloneCodeEditor*/ {
	var item;
	if (item = activateItem('editor:'+filename)) return null;
	layout.selectedItem.addChild({
		id: "editor:"+filename,
		type:'component',
		title: filename,
		componentName: 'editor',
		componentState: { filename: filename },
	});
}
export function openTerminal(id : string) : xterm.Terminal {
	var item;
	if (!(item = activateItem('terminal:'+id))){
		item = layout.createContentItem({
			id: "terminal:"+id,
			type:'component',
			title: id,
			componentName: 'terminal',
			componentState: {  },
		}, layout.selectedItem);
		layout.selectedItem.addChild(item);
	}
	return (<any>item).instance;
}
export function startApp() {
	
	if ("layoutConfig" in window.localStorage) {
		layoutConfig = JSON.parse(window.localStorage["layoutConfig"]);
	}
	layoutConfig.settings.selectionEnabled = true;
	layout = new GoldenLayout( layoutConfig );
	layout.on( 'stateChanged', function(){
		var state = JSON.stringify( layout.toConfig() );
		localStorage.setItem( 'layoutConfig', state );
	});
	layout.on( 'selectionChanged', function(e:any){
		console.log("selection changed",e)
	});
	
	
	layout.registerComponent( 'editor', function( container:any, state:any ){
		var editor = globalEditor = monaco.editor.create(container.getElement()[0]!!, {
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
					return rpc.exec('parse_pcap_file_with_scapy', {'pcap_filename':"pcaps/AP-SOPPALCO.pcap", 'script_filename':state.filename})
				})
				.then(function(response : any) {
					var returnCode = response[0], enc_data = response[1], stderr = response[2];
					
					var term = openTerminal("log");
					term.write((stderr+"\n").replace(/\n/g, "\r\n"));
					if (returnCode != 0) {
						//var errstring = new TextDecoder("utf-8").decode(enc_data);
						//alert("Error: " + returnCode + "\n" + stderr);
						term.write("\x1b[38;5;9mCommand returned error code "+returnCode+"\x1b[0m\r\n");
					}
					term.write("\r\n");
					//alert("OK");
					hexView.showHex(enc_data);
					
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
		var grid = pg = new PacketGrid(container.getElement()[0], ["time", "IP.src", "IP.dst"]);
		container.on("resize", function() {
			grid.resizeCanvas();
		})
		grid.onItemClick.on(function(data) {
			hexView.showPacketHex(data._packetData.f);
			packetDetail.setData(
				data._packetData.f.map((x:any[])=>({ 
					proto:x[0], field:x[1], display:x[2], raw:bufferToHex(x[3]) 
				})), 
				false);
		});
	});
	layout.registerComponent( 'filelist', function( container:any, state:any ){
		var fl = new FileList(container.getElement()[0], state.dir);
		fl.onItemClick.on(function(item) {
			var filename = fl.dir + item.name;
			//alert(filename)
			openEditor(filename);
		});
		container.on("resize", function() {
			fl.resizeCanvas();
		})
	});

	layout.registerComponent( 'hexdump', function( container:any, state:any ){
		return hexView = new HexView(container.getElement()[0]);
	});
	layout.registerComponent( 'packetdetail', function( container:any, state:any ){
		return packetDetail = new GridCtrl(container.getElement()[0], ['proto','field','display','raw']);
	});
	layout.registerComponent( 'terminal', function( container:any, state:any ){
		console.log(TerminalConstructor)
		var term = new TerminalConstructor({});
		container.on("open", function() {
			term.open(container.getElement()[0]);
		})
		container.on("resize", function() {
			//@ts-ignore
			try{term.fit();}catch(ex){console.warn("failed to fit terminal",term)}
		})
		return term;
	});

	rpc.init(function() {
		rpc.exec("login", {"name":"aaa"});
		layout.init();
	})

}
