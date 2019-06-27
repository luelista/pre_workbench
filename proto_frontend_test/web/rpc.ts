import { encode, decode } from 'cbor/cbor';
import * as Status from 'statusIndicator';

let socket : WebSocket;

var reqId = 1;
var requests : any = {};
export function exec(cmd : string, args : any) {
	var id = reqId++;
	Status.showProgress();
	return new Promise((resolve, reject) => {
		requests[id] = [resolve, reject];
		var request = encode({ "id": id, "cmd": cmd, "args": args });
		console.log("Request:",request);
		socket.send(request);
	});
}
function handleResponse(response_binary : ArrayBuffer) {
	var response = decode(response_binary);
	console.log("Response:",response);
	var request = requests[response.id];
	if (response.error) {
		request[1](response.error);
		Status.show("error", response.error, 4000);
	} else {
		request[0](response.ans);
	}
	if (!('progress' in response)) {
		delete requests[response.id];
		Status.hideProgress();
	}
}
export function init(cb : EventListener) {
	socket = new WebSocket("ws://localhost:5678")
	socket.addEventListener("open", cb);
	socket.onmessage = function(event) {
		let blob : Blob = event.data; 
		let reader = new FileReader();
		reader.onload = function() {
			handleResponse(<ArrayBuffer> reader.result);
		};
		reader.readAsArrayBuffer(blob)
	};
}
