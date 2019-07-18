import { encode, decode } from 'cbor/cbor';
import * as Status from 'statusIndicator';

const OP_CALL = 1;
const OP_ANSWER = 2;
const OP_ANSWERERROR = 3;
const OP_FAIL = 4;

let socket : WebSocket;

var reqId = 1;
var requests : any = {};
export function exec(cmd : string, args : any) : Promise<any> {
	var id = reqId++;
	Status.showProgress();
	return new Promise<any>((resolve, reject) => {
		requests[id] = [resolve, reject];
		var request = encode([ OP_CALL, id, 0, "0", cmd, args ]);
		console.log("Request:",request);
		socket.send(request);
	});
}
export function callMethod(oid : number|string, iid : string, cmd : string, args : any) : Promise<any> {
	var id = reqId++;
	Status.showProgress();
	return new Promise<any>((resolve, reject) => {
		requests[id] = [resolve, reject];
		var request = encode([ OP_CALL, id, oid, iid, cmd, args ]);
		console.log("Request:",request);
		socket.send(request);
	});
}
function handleResponse(response_binary : ArrayBuffer) {
	var response = decode(response_binary);
	console.log("Response:",response);
	var op = response[0], request_id  = response[1];
	switch(op) {
	case OP_ANSWER:
		var request = requests[request_id];
		request[0](response[2]);
		delete requests[request_id];
		Status.hideProgress();
		break;
	case OP_ANSWERERROR:
		var request = requests[request_id];
		request[1](response[3]);
		Status.show("error", response[3], 4000);
	}
	/*if (!('progress' in response)) {
		delete requests[response.id];
		Status.hideProgress();
	}*/
}
export function init(cb : EventListener) {
	Status.showProgress();
	socket = new WebSocket("ws://localhost:5678")
	socket.addEventListener("open", cb);
	socket.addEventListener("open", () => Status.hideProgress());
	socket.onmessage = function(event) {
		let blob : Blob = event.data; 
		let reader = new FileReader();
		reader.onload = function() {
			handleResponse(<ArrayBuffer> reader.result);
		};
		reader.readAsArrayBuffer(blob)
	};
	socket.onerror = function(e) {
		Status.hideProgress()
		console.warn("Websocket error",e)
	}
	socket.onclose = function(e) {
		console.warn("Websocket closed",e)
		Status.show("error", "Websocket closed", null);
		setTimeout(function() {
			init(function() {
				Status.hide("error");
			});
		}, 2000);
	}
}
