#!/usr/bin/env python

# WS server example

import asyncio, functools, ssl
import websockets
import cbor, json, struct
import tempfile
import subprocess
import os, time, inspect

from http import HTTPStatus
from pdml_helper import convertPdmlToPacketTree
from collections import defaultdict

this_dir = os.path.dirname(os.path.realpath(__file__))
server_root = os.path.join(this_dir, "web")
datadir_root = os.path.join(this_dir, "data/")

RPC_OP_CALL = 1
RPC_OP_ANSWER = 2
RPC_OP_ANSWERERROR = 3
RPC_OP_FAIL = 4


METHODS = defaultdict(lambda: dict())

def RpcMethod(iface, name=None):
	def decorator_RpcMethod(func):
		if name == None: name = func.__name__
		#METHODS[iface][name] = func
		func._rpc_interface_id = iface
		func._rpc_method_id = name
		return func
	return decorator_RpcMethod

class PFT_Server:
	@RpcMethod(iface="pft",name="parse_pcap_file_with_scapy")
	def parse_pcap_file_with_scapy(self, pcap_filename, script_filename):
		fd, tmpout = tempfile.mkstemp(".cbor")
		result = subprocess.run(["python3", "wrapper.py", "data/" + script_filename, "data/" + pcap_filename, tmpout], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		tmpfile = os.fdopen(fd, "rb")
		out = tmpfile.read()
		tmpfile.close()
		os.unlink(tmpout)
		return [result.returncode, out, result.stdout.decode("utf8")]

	def _readerthread(self, fh, buffer):
		buffer.append(fh.read())
		fh.close()

	"""
	@RpcMethod(iface="pft",name="parse_pcap_file_with_scapy2")
	async def parse_pcap_file_with_scapy2(self, pcap_filename, script_filename):
		read_fd, write_fd = os.pipe()
		proc = subprocess.Popen(["python3", "wrapper.py", "data/" + script_filename, "data/" + pcap_filename, str(write_fd)], 
			stdout=subprocess.PIPE,stderr=subprocess.PIPE, pass_fds=[write_fd])
		mypipe_buff = []
		mypipe = os.fdopen(read_fd, "rb")
		mypipe_thread = threading.Thread(target=self._readerthread, args=(mypipe, mypipe_buff), daemon=True)
		mypipe_thread.start()
		stdout, stderr = proc.communicate(timeout=5000)

		return [result.returncode, result.stdout, result.stderr.decode("utf8")]
	"""
	@RpcMethod(iface="pft",name="parse_pcap_file_with_tshark")
	def parse_pcap_file_with_tshark(self, pcap_filename):
		result = subprocess.run(["tshark", "-r", "data/" + pcap_filename, "-T", "pdml"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		return [result.returncode, cbor.dumps(convertPdmlToPacketTree(result.stdout)), result.stderr.decode("utf8")]


	@RpcMethod(iface="pft",name="login")
	async def login_rpc(self, name):
		print("login ",name)
		await asyncio.sleep(1)
		print("done ",name)
		return "Hello "+name+"!"


	@RpcMethod(iface="pft",name="testasync")
	async def testasync(self, name):
		print("testasync ",name)
		await asyncio.sleep(1)
		print("testasync done ",name)
		return "testasync "+name+"!"


	@RpcMethod(iface="pft",name="testthread")
	def testthread(self, name):
		print("testthread ",name)
		time.sleep(1)
		print("testthread done ",name)
		return "testthread "+name+"!"

	@RpcMethod(iface="pft")
	async def listdir(self, dir):
		path = datadir_root + dir
		return [dict(zip('mode ino dev nlink uid gid size atime mtime ctime'.split(), os.stat( os.path.join(path, n) )) , name=n) 
			for n in os.listdir(path)]

	@RpcMethod(iface="pft")
	async def getscript(self, file):
		with open(os.path.join(datadir_root, file), "r") as f:
			return f.read()

	@RpcMethod(iface="pft")
	async def putscript(self, file, content):
		with open(os.path.join(datadir_root, file), "w") as f:
			f.write(content)

	@RpcMethod(iface="http",name="get")
	async def respond_to_get_request(self, path, **kw):
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
	def get_mimetype(self, path):
		root, ext = os.path.splitext(path)
		if ext in types:
			return types[ext]
		else:
			return "application/octet-stream"


class RpcObject:
	pass
class LocalObjectProxy(RpcObject):
	def __init__(self, instance, objectPath=None):
		self.interfaceDefs = defaultdict(lambda: dict())
		for funcName in dir(obj):
			member = getattr(obj, funcName)
			if callable(member) and hasattr(member, "_rpc_method_id"):
				self.interfaceDefs[member._rpc_interface_id][member._rpc_method_id] = {"name": funcName, "args":[p.name for p in inspect.signature(member).parameters]}
		self.interfaceDefs["Introspectable"] = {"introspect":{"name":"introspect","args":[]}}
		self.interfaces = list(self.interfaceDefs.keys())
		self.objectPath = objectPath


class RpcBroker:
	def __init__(self):
		self.objects = {}
		self.nextObjectId = 0
	def addObject(self, obj):
		METHODS = defaultdict(lambda: dict())
		for funcName in dir(obj):
			member = getattr(obj, funcName)
			if callable(member) and hasattr(member, "_rpc_method_id"):
				METHODS[member._rpc_interface_id][member._rpc_method_id] = member
		id = self.nextObjectId
		self.nextObjectId += 1
		self.objects[id] = []


async def rpc_method_call(socket, request_id, object_id, interface_id, method_id, params):
	try:
		if object_id != 1: raise Exception("object not found")
		method = METHODS[interface_id][method_id]
		#response = await method(**params)
		if inspect.iscoroutinefunction(method):
			print("Calling async "+method_id)
			task = asyncio.ensure_future(method(**params))
		else:
			print("Calling in threadpool "+method_id)
			task = asyncio.get_event_loop().run_in_executor(None, functools.partial(method, **params))
		response = await task
		await socket.send([ RPC_OP_ANSWER, request_id, response ])
	except Exception as e:
		print("Sending error response")
		print(e)
		await socket.send([ RPC_OP_ANSWERERROR, request_id, 2, str(e), {} ])

##################################################################################################################



class WsRpcHandler:
	def __init__(self, socket, path):
		self.socket = socket

	async def send(self, data):
		await self.socket.send(cbor.dumps(data))

	async def run_loop(self):
		while True:
			request_str = await self.socket.recv()
			request = cbor.loads(request_str)
			if request[0] == RPC_OP_CALL:
				op_code, request_id, object_id, interface_id, method_id, params = request
				asyncio.ensure_future(rpc_method_call(self, request_id, object_id, interface_id, method_id, params))
async def ws_rpc_conn_handler(socket, path):
	h = WsRpcHandler(socket, path)
	await h.run_loop()

class WebSocketServerProtocolWithHTTP(websockets.WebSocketServerProtocol):
	"""Implements a simple static file server for WebSocketServer"""

	async def process_request(self, path, request_headers):
		"""Serves a file when doing a GET request with a valid path"""

		if "Upgrade" in request_headers:
			return  # Probably a WebSocket connection

		code, response_headers, body = await respond_to_get_request(path)

		response_headers.append(('Server', "asyncio"))
		response_headers.append(('Connection', "close"))
		response_headers.append(('Content-Length', str(len(body))))

		return code, response_headers, body

#start_server = websockets.serve(ws_rpc_conn_handler, 'localhost', 5678, create_protocol=WebSocketServerProtocolWithHTTP)
#print("Listening http://localhost:5678")
#asyncio.get_event_loop().run_until_complete(start_server)


##################################################################################################################

class JsonTcpRpcHandler:
	async def send(self, data):
		self.writer.write(json.dumps(data).encode("utf-8") + b"\n")
		await self.writer.drain()

	async def run_loop(self, loop):
		# WARNING: no cert checking
		sc = ssl.SSLContext()
		#sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='selfsigned.cert')

		reader, writer = await asyncio.open_connection(
			'localhost', 2344, ssl=sc, loop=loop)
		self.writer = writer
		await self.send([1,0,0,"ObjectBroker","add",{"interfaces":list(METHODS.keys()),"alias_index":1}])
		while True:
			request_str = await reader.readline()
			if request_str == b'': break
			print("Client received {!r} from server".format(request_str))
			request = json.loads(request_str.decode("utf-8"))
			if request[0] == RPC_OP_CALL:
				op_code, request_id, object_id, interface_id, method_id, params = request
				asyncio.ensure_future(rpc_method_call(self, request_id, object_id, interface_id, method_id, params))
		writer.close()
		print('Client done')


class LengthPrefixedCborTcpRpcHandler:
	async def send(self, data):
		buf = cbor.dumps(data)
		self.writer.write(struct.pack("!I", len(buf)) + buf)
		await self.writer.drain()

	async def run_loop(self, loop):
		while True:
			try:
				# WARNING: no cert checking
				sc = ssl.SSLContext()
				#sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='selfsigned.cert')

				reader, writer = await asyncio.open_connection(
					'localhost', 2344, ssl=sc, loop=loop)
				print("RPC connected")
				self.writer = writer
				await self.send([1,0,0,"ObjectBroker","add",{"interfaces":list(METHODS.keys()),"alias_index":1}])
				while True:
					header_buf = await reader.readexactly(4)
					print(header_buf)
					if len(header_buf) != 4: break
					frame_len, = struct.unpack("!I", header_buf)
					#print("Received frame_len=",frame_len)
					frame_buf = await reader.readexactly(frame_len)
					#print("Client received {!r} from server".format(frame_buf))
					request = cbor.loads(frame_buf)
					print(request)
					if request[0] == RPC_OP_CALL:
						op_code, request_id, object_id, interface_id, method_id, params = request
						asyncio.ensure_future(rpc_method_call(self, request_id, object_id, interface_id, method_id, params))
				writer.close()
				print('Client done')
			except:
				pass
			print("RPC connection closed, trying again")
			await asyncio.sleep(1)

tcp_client = LengthPrefixedCborTcpRpcHandler()
asyncio.ensure_future(tcp_client.run_loop(asyncio.get_event_loop()))


asyncio.get_event_loop().run_forever()
