
# PRE Workbench
# Copyright (C) 2019 Max Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import asyncio, functools, ssl, json, struct
import websockets
from collections import defaultdict
import inspect, traceback

loop = asyncio.get_event_loop()

RPC_OP_CALL = 1
RPC_OP_ANSWER = 2
RPC_OP_ANSWERERROR = 3
RPC_OP_FAIL = 4

def RpcMethod(iface, name=None):
	def decorator_RpcMethod(func):
		nonlocal name
		if name == None: name = func.__name__
		#METHODS[iface][name] = func
		func._rpc_interface_id = iface
		func._rpc_method_id = name
		return func
	return decorator_RpcMethod


class RpcObject:
	pass

class LocalObjectProxy(RpcObject):
	def __init__(self, instance, objectPath=None):
		self.interfaceDefs = defaultdict(lambda: dict())
		self.methods = defaultdict(lambda: dict())
		for funcName in dir(instance):
			member = getattr(instance, funcName)
			if callable(member) and hasattr(member, "_rpc_method_id"):
				self.interfaceDefs[member._rpc_interface_id][member._rpc_method_id] = {"name": member._rpc_method_id, "args": list(inspect.signature(member).parameters.keys())}
				self.methods[member._rpc_interface_id][member._rpc_method_id] = member
		self.interfaceDefs["Introspectable"] = {"introspect":{"name":"introspect","args":[]}}
		self.methods["Introspectable"]["introspect"] = self.introspect
		self.interfaces = list(self.interfaceDefs.keys())
		self.objectPath = objectPath
		self.instance = instance

	async def introspect(self):
		return self.interfaceDefs

	async def methodCall(self, interface_id, method_id, params, source):
		try:
			method = self.methods[interface_id][method_id]
		except KeyError:
			raise Exception("rpc method "+interface_id+"."+method_id+" not found")
		#response = await method(**params)
		if inspect.iscoroutinefunction(method):
			print("Calling async "+method_id)
			return await method(**params)
		else:
			print("Calling in threadpool "+method_id)
			return await loop.run_in_executor(None, functools.partial(method, **params))


class RpcObjectContainer:
	def __init__(self):
		self.objects = {}
		self.objectsByPath = {}
		self.nextObjectId = 0

	def createObject(self, objectPath=None):
		def wrapper(cls):
			inst = cls()
			self.addObject(LocalObjectProxy(inst, objectPath))
			return cls
		return wrapper

	def addObject(self, obj):
		id = self.nextObjectId
		self.nextObjectId += 1
		self.objects[id] = obj
		if hasattr(obj, "objectPath"): self.objectsByPath[obj.objectPath] = obj
		obj.objectIndex = id
		#print("RpcClient object registered",id,obj)
		return id
		
	async def methodCalled(self, objectId, interfaceId, method, params, source):
		if type(objectId) is str:
			d = self.objectsByPath
		else:
			d = self.objects
		if not (objectId in d): raise Exception("object not found")
		return await d[objectId].methodCall(interfaceId, method, params, source)

class RpcClient(RpcObjectContainer):
	async def connectionEstablished(self, connection):
		print("RpcClient connectionEstablished",self.objects,connection)
		for oid, o in self.objects.items():
			remote_id = await connection.remoteMethodCall(0, "ObjectBroker", "add", alias_index=oid, interfaces=o.interfaces, object_path=o.objectPath)
			print("registered %r (%r) at remote_id %r"%(oid, o, remote_id))



class RpcBroker(RpcObjectContainer):
	def __init__(self):
		super().__init__()
		self.addObject(LocalObjectProxy(self, "/"))
	async def connectionEstablished(self, connection):
		print("RpcBroker connectionEstablished",self.objects,connection)

	@RpcMethod("ObjectBroker")
	def add(self, interfaces, alias_index=None, object_path=None):
		pass

	@RpcMethod("ObjectBroker")
	def list(self):
		return [{'oid':o.objectIndex,'path':o.objectPath,'interfaces':o.interfaces} for o in self.objects.values()]

	@RpcMethod("ObjectBroker")
	def getImplementingObjects(self, iid):
		return [{'oid':o.objectIndex,'path':o.objectPath,'interfaces':o.interfaces} for o in self.objects.values() if iid in o.interfaces]


class AbstractRpcConnection:
	def __init__(self, handler):
		self.futures = dict()
		self._nextRequestId = 0
		self.handler = handler
	async def remoteMethodCall(self, objectIndex, interfaceId, method, **params):
		id = self._nextRequestId
		self._nextRequestId += 1
		futu = loop.create_future()
		self.futures[id] = futu
		await self.send([RPC_OP_CALL, id, objectIndex, interfaceId, method, params])
		return await futu
	async def connectionEstablished(self):
		asyncio.ensure_future(self.handler.connectionEstablished(self))
	async def handleData(self, data):
		if data[0] == RPC_OP_CALL:
			asyncio.ensure_future(self.handleCall(data[1], data[2], data[3], data[4], data[5]))
		elif data[0] == RPC_OP_ANSWER or data[0] == RPC_OP_ANSWERERROR:
			request_id = data[1]
			futu = self.futures[request_id]
			del self.futures[request_id]
			if data[0] == RPC_OP_ANSWER:
				futu.set_result(data[2])
			else:
				futu.set_exception(Exception(data[3]))
		elif data[0] == RPC_OP_FAIL:
			print("OP_FAIL",data)
		else:
			print("invalid op received",data)
			await self.send([RPC_OP_FAIL,3,"invalid op"])
	async def handleCall(self, request_id, object_id, interface_id, method_id, params):
		try:
			response = await self.handler.methodCalled(object_id, interface_id, method_id, params, self)
			await self.send([ RPC_OP_ANSWER, request_id, response ])
		except Exception as e:
			print("Sending error response")
			traceback.print_exc()
			await self.send([ RPC_OP_ANSWERERROR, request_id, 2, traceback.format_exc(), {} ])

##################################################################################################################

class JsonTcpRpcConnection(AbstractRpcConnection):
	def __init__(self, handler, target):
		super().__init__(handler)
		self.targetHost, self.targetPort = target.split(":")

	async def send(self, data):
		self.writer.write(json.dumps(data).encode("utf-8") + b"\n")
		await self.writer.drain()

	async def run_loop(self, loop):
		# WARNING: no cert checking
		sc = ssl.SSLContext()
		#sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='selfsigned.cert')

		self.reader, self.writer = await asyncio.open_connection(
			self.targetHost, self.targetPort, ssl=sc, loop=loop)
		#await self.send([1,0,0,"ObjectBroker","add",{"interfaces":list(METHODS.keys()),"alias_index":1}])
		await self.connectionEstablished()
		while True:
			request_str = await self.reader.readline()
			if request_str == b'': break
			print("Client received {!r} from server".format(request_str))
			request = json.loads(request_str.decode("utf-8"))
			await self.handleData(request)
		self.writer.close()
		print('Client done')


class LengthPrefixedEncodedTcpRpcConnection(AbstractRpcConnection):
	def __init__(self, handler, target, encoder):
		super().__init__(handler)
		self._drain_lock = asyncio.Lock(loop=loop)
		self.targetHost, self.targetPort = target.split(":")
		self.encoder = encoder

	async def send(self, data):
		buf = self.encoder.dumps(data)
		print("sending %d cbor bytes"%(len(buf)),data[0],data[1])
		self.writer.write(struct.pack("!I", len(buf)) + buf)
		# drain() cannot be called concurrently by multiple coroutines:
		# http://bugs.python.org/issue29930. Remove this lock when no
		# version of Python where this bugs exists is supported anymore.
		with (await self._drain_lock):
			# Handle flow control automatically.
			await self.writer.drain()

	async def run_loop(self, loop):
		while True:
			try:
				sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='ca.pem')
				sc.load_cert_chain("client.pem")

				self.reader, self.writer = await asyncio.open_connection(
					self.targetHost, self.targetPort, ssl=sc, loop=loop)
				#await self.send([1,0,0,"ObjectBroker","add",{"interfaces":list(METHODS.keys()),"alias_index":1}])
				await self.connectionEstablished()
				while True:
					header_buf = await self.reader.readexactly(4)
					if len(header_buf) != 4: break
					frame_len, = struct.unpack("!I", header_buf)
					frame_buf = await self.reader.readexactly(frame_len)
					request = self.encoder.loads(frame_buf)
					print("encoded request received: ",request)
					await self.handleData(request)
				self.writer.close()
				print('Client done')
			except Exception as ex:
				print("Error:",ex)
				
			print("RPC connection closed, trying again")
			await asyncio.sleep(1)

