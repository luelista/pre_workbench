#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import cbor
import tempfile
import subprocess
import os

from http import HTTPStatus

this_dir = os.path.dirname(os.path.realpath(__file__))
server_root = os.path.join(this_dir, "web")
datadir_root = os.path.join(this_dir, "data/")


METHODS = {}
def register_rpc(name):
	def decorator_register_rpc(func):
		METHODS[name] = func
		return func
	return decorator_register_rpc

@register_rpc("parse_pcap_file")
def parse_pcap_file(pcap_filename, script_filename):
	result = subprocess.run(["python3", "wrapper.py", "data/" + script_filename, pcap_filename], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return [result.returncode, result.stdout, result.stderr.decode("utf8")]


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

		if path == '/':
			path = '/index.html'

		response_headers = [
			('Server', 'asyncio'),
			('Connection', 'close'),
			('Content-Type', get_mimetype(path))
		]
		
		full_path = os.path.realpath(os.path.join(server_root, path[1:]))

		print("GET", path, end=' ')

		# Validate the path
		if os.path.commonpath((server_root, full_path)) != server_root or \
				not os.path.exists(full_path) or not os.path.isfile(full_path):
			print("404 NOT FOUND")
			return HTTPStatus.NOT_FOUND, [], b'404 NOT FOUND'

		print("200 OK")
		body = open(full_path, 'rb').read()
		response_headers.append(('Content-Length', str(len(body))))
		return HTTPStatus.OK, response_headers, body

async def hello(websocket, path):
	while True:
		request_str = await websocket.recv()
		request = cbor.loads(request_str)
		#print("Request:",request)
		print("Calling "+request['cmd'])
		try:
			method = METHODS[request['cmd']]
			response = method(**request['args'])
			#print("Answer:", response)
			await websocket.send(cbor.dumps({ 'id': request['id'], 'ans': response }))
		except Exception as e:
			print("Sending error response")
			print(e)
			await websocket.send(cbor.dumps({ 'id': request['id'], 'error': str(e) }))
		

start_server = websockets.serve(hello, 'localhost', 5678, create_protocol=WebSocketServerProtocolWithHTTP)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


