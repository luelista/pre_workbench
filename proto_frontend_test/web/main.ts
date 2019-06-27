
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

var scriptfilename = 'hallo.py';
var pcapfilename = '../test.pcap';


export function startApp() {

	var editor = monaco.editor.create(document.getElementById('container')!!, {
		value: [
			'# eile mit weile'
		].join('\n'),
		language: 'python'
	});
	editor.getModel()!!.updateOptions({insertSpaces:false});

	rpc.init(function() {
		rpc.exec("test", {"name":"aaa"});
		rpc.exec('getscript', {'file':scriptfilename}).then(function(result) {
			editor.setValue(<string>result);
		})

	})
	editor.onKeyUp(function(e) {
		if (e.code == "Enter" && e.ctrlKey) {
			rpc.exec('parse_pcap_file', {'pcap_filename':pcapfilename, 'scapycode':editor.getValue()})
			.then(function(response) {
				console.log(response);
			});
		}
		if (e.code == "KeyS" && e.ctrlKey) {
			console.log("Save...");
			rpc.exec('putscript', {'file':scriptfilename, 'content':editor.getValue()})
			.then(function() {
				console.log("Saved");
			});
		}
	})
}
