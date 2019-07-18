#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import cbor
import tempfile
import subprocess
import os

from http import HTTPStatus
from pdml_helper import convertPdmlToPacketTree

this_dir = os.path.dirname(os.path.realpath(__file__))
server_root = os.path.join(this_dir, "web")
datadir_root = os.path.join(this_dir, "data/")

RPC_OP_CALL = 1
RPC_OP_ANSWER = 2
RPC_OP_ANSWERERROR = 3
RPC_OP_FAIL = 4


METHODS = {}
def register_rpc(name):
	def decorator_register_rpc(func):
		METHODS[name] = func
		return func
	return decorator_register_rpc

@register_rpc("parse_pcap_file_with_scapy")
def parse_pcap_file_with_scapy(pcap_filename, script_filename):
	fd, tmpout = tempfile.mkstemp(".cbor")
	result = subprocess.run(["python3", "wrapper.py", "data/" + script_filename, "data/" + pcap_filename, tmpout], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	tmpfile = os.fdopen(fd, "rb")
	out = tmpfile.read()
	tmpfile.close()
	os.unlink(tmpout)
	return [result.returncode, out, result.stdout.decode("utf8")]

def _readerthread(fh, buffer):
	buffer.append(fh.read())
	fh.close()

"""
@register_rpc("parse_pcap_file_with_scapy2")
def parse_pcap_file_with_scapy2(pcap_filename, script_filename):
	read_fd, write_fd = os.pipe()
	proc = subprocess.Popen(["python3", "wrapper.py", "data/" + script_filename, "data/" + pcap_filename, str(write_fd)], 
		stdout=subprocess.PIPE,stderr=subprocess.PIPE, pass_fds=[write_fd])
	mypipe_buff = []
	mypipe = os.fdopen(read_fd, "rb")
	mypipe_thread = threading.Thread(target=_readerthread, args=(mypipe, mypipe_buff), daemon=True)
	mypipe_thread.start()
	stdout, stderr = proc.communicate(timeout=5000)

	return [result.returncode, result.stdout, result.stderr.decode("utf8")]
"""
@register_rpc("parse_pcap_file_with_tshark")
def parse_pcap_file_with_tshark(pcap_filename):
	result = subprocess.run(["tshark", "-r", "data/" + pcap_filename, "-T", "pdml"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return [result.returncode, cbor.dumps(convertPdmlToPacketTree(result.stdout)), result.stderr.decode("utf8")]


@register_rpc("login")
def login_rpc(name):
	return "Hello "+name+"!"

@register_rpc("listdir")
def listdir_rpc(dir):
	path = datadir_root + dir
	return [dict(zip('mode ino dev nlink uid gid size atime mtime ctime'.split(), os.stat( os.path.join(path, n) )) , name=n) 
		for n in os.listdir(path)]

@register_rpc("getscript")
def getscript_rpc(file):
	with open(os.path.join(datadir_root, file), "r") as f:
		return f.read()

@register_rpc("putscript")
def putscript_rpc(file, content):
	with open(os.path.join(datadir_root, file), "w") as f:
		f.write(content)

@register_rpc("http_get")
def respond_to_get_request(path, **kw):
	if path == '/':
		path = '/index.html'

	full_path = os.path.realpath(os.path.join(server_root, path[1:]))

	print("GET", path, end=' ')

	# Validate the path
	if os.path.commonpath((server_root, full_path)) != server_root or \
			not os.path.exists(full_path) or not os.path.isfile(full_path):
		print("404 NOT FOUND")
		return HTTPStatus.NOT_FOUND, [], b'404 NOT FOUND'

	print("200 OK")
	body = open(full_path, 'rb').read()
	return [HTTPStatus.OK, [
		('Content-Type', get_mimetype(path))
	], body]

types={".html":"text/html",".js":"text/javascript",".css":"text/css"}
def get_mimetype(path):
	root, ext = os.path.splitext(path)
	if ext in types:
		return types[ext]
	else:
		return "application/octet-stream"


class WebSocketServerProtocolWithHTTP(websockets.WebSocketServerProtocol):
	"""Implements a simple static file server for WebSocketServer"""

	async def process_request(self, path, request_headers):
		"""Serves a file when doing a GET request with a valid path"""

		if "Upgrade" in request_headers:
			return  # Probably a WebSocket connection

		code, response_headers, body = respond_to_get_request(path)

		response_headers.append(('Server', "asyncio"))
		response_headers.append(('Connection', "close"))
		response_headers.append(('Content-Length', str(len(body))))

		return code, response_headers, body

async def hello(websocket, path):
	while True:
		request_str = await websocket.recv()
		request = cbor.loads(request_str)
		op_code = request[0]
		if op_code == RPC_OP_CALL:
			op_code, request_id, object_id, interface_id, method_id, params = request
			#print("Request:",request)
			print("Calling "+method_id)
			try:
				method = METHODS[method_id]
				response = method(**params)
				#print("Answer:", response)
				await websocket.send(cbor.dumps([ RPC_OP_ANSWER, request_id, response ]))
			except Exception as e:
				print("Sending error response")
				print(e)
				await websocket.send(cbor.dumps([ RPC_OP_ANSWERERROR, request_id, 1, str(e), {} ]))
		

start_server = websockets.serve(hello, 'localhost', 5678, create_protocol=WebSocketServerProtocolWithHTTP)
print("Listening http://localhost:5678")

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


