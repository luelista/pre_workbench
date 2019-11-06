import asyncio
import binascii
import heapq
import os
import re
import ssl
import struct
import time

import pyhy

from pre_workbench.structinfo import xdrm


def void(*args):
	return None

class ConnectionManager:
	def __init__(self, netkey=None, keypair=None, **params):
		self.loop = asyncio.get_event_loop()
		self.transports = list()
		self.peers = list()
		self.sessions_by_id = dict()
		self.sessions_by_peer_key = dict()
		if netkey is None:
			self.netkey = pyhy.hydro_secretbox_keygen()
		else:
			self.netkey = netkey
		self.keypair = KeyPair(keypair)
		print("my public key: ",binascii.hexlify(self.keypair.sign_pk))
		print("netkey: ",binascii.hexlify(self.netkey))
		self.proto_handler_registry = dict()
		self.proto_handler_registry["rpcnet.Handshake"] = lambda channel: void(asyncio.ensure_future(channel.session.start_kx_responder(channel), self.loop))
		asyncio.ensure_future(self._advertise_loop(), loop=self.loop)

	def saveParams(self):
		return {"netkey":self.netkey, "keypair":self.keypair.raw()}

	async def _advertise_loop(self):
		while True:
			await asyncio.sleep(5)
			print("gathering addresses for advertising")
			transport_addresses = await asyncio.gather(*(transport.getSelfAddresses() for transport in self.transports))
			addresses = [a for x in transport_addresses
							for a in x ]
			meta = { "id": self.keypair.sign_pk, "adr": addresses, }
			print("advertising",meta)
			await asyncio.gather(*(transport.advertise(meta) for transport in self.transports))


	async def add_transport(self, clz, addr):
		obj = clz(self, addr)
		self.transports.append(obj)
		await obj.run()

	def make_proto_handler(self, channel):
		return self.proto_handler_registry[channel.meta['proto']](channel)

	async def createChannel(self, peer_id, proto_id):
		sess = await self.getPeerSession(peer_id)
		return sess.create_channel(proto_id)

	async def getPeerSession(self, peer_id):
		try:
			return self.sessions_by_peer_key[peer_id]
		except KeyError:
			#conn = await self.getPeerConnection(peer_id)
			sess = EncryptedSession(None, self, is_responder=False, peer_id=peer_id)
			self.sessions_by_peer_key[peer_id] = sess
			await sess.ensure_connected()
			return sess

	#async def getPeerConnection(self, peer_id):

	def handleAdvertise(self, meta):
		print("advertise received",meta)

	def handleSessionData(self, session_id, data, sender):
		try:
			sess = self.sessions_by_id[session_id]
		except KeyError:
			sess = EncryptedSession(sender, self, is_responder=True)
			self.sessions_by_id[session_id] = sess
		sess.handleSessionData(data, sender)

class RpcChannel:
	TYPE_MASK = 0x000f
	TYPE_CREATE = 0x0001
	TYPE_MSG_FRAG = 0x0002
	TYPE_MSG_FIN = 0x0003
	TYPE_SHUTDOWN = 0x0004
	TYPE_MSG_ACK = 0x0005

	RETR_AFTER_SECS = 2

	def __init__(self, chan_id, session, proto_handler=None):
		self.meta = None
		self.id = chan_id
		self.buffer = list()
		self.proto_handler = proto_handler
		self.session = session
		self.recv_queue = asyncio.Queue()
		self.send_queue = list()
		self.retr_queue = list()
		self.retr_msg_no = 0
		self.send_msg_no = 0
		self.recv_msg_no = 0
		self.recv_msg_offset = 0
		self.ooo_buf = list()
		self.retransmit_timeout_handle = None

	async def recv_msg(self):
		return self.recv_queue.get()

	async def handleChunk(self, flags, msg_no, msg_offset, data):
		frame_type = flags & RpcChannel.TYPE_MASK
		if frame_type == RpcChannel.TYPE_MSG_ACK:
			ack_msg_no, = struct.unpack_from("!I", data)
			ack_count = ack_msg_no - self.retr_msg_no
			if ack_count < 1: return
			self.retr_queue = self.retr_queue[ack_count:]
			self.retr_msg_no = ack_msg_no
		else:
			if msg_no != self.recv_msg_no or msg_offset != self.recv_msg_offset:
				heapq.heappush(self.ooo_buf, (msg_no, msg_offset, flags, data))
			else:
				await self.handleDataChunk(flags, msg_no, msg_offset, data)
				while self.ooo_buf[0][0] == self.recv_msg_no and self.ooo_buf[0][1] == self.recv_msg_offset:
					flags, msg_no, msg_offset, data = heapq.heappop(self.ooo_buf)
					await self.handleDataChunk(flags, msg_no, msg_offset, data)

	async def handleDataChunk(self, flags, msg_no, msg_offset, data):
		frame_type = flags & RpcChannel.TYPE_MASK
		if frame_type == RpcChannel.TYPE_MSG_FRAG:
			self.buffer.append(data)
			self.recv_msg_offset += len(data)
		elif frame_type == RpcChannel.TYPE_MSG_FIN:
			b, self.buffer = self.buffer + [data], []
			await self.session.send_chan_frame(self.id, RpcChannel.TYPE_MSG_ACK, struct.pack("!I", msg_no))
			self.recv_msg_no, self.recv_msg_offset = self.recv_msg_no + 1, 0
			if self.meta is None:
				self.meta = xdrm.loads(b)
				self.proto_handler = self.session.handler.make_proto_handler(self)
			elif self.proto_handler is None:
				await self.recv_queue.put(b)
			else:
				await self.proto_handler.datagram_received(b''.join(b))

	async def send_msg(self, data):
		await self._transmit_msg(data, self.send_msg_no)
		self.send_msg_no += 1
		self.retr_queue.append((time.time(), data))
		if self.retransmit_timeout_handle is None:
			self.retransmit_timeout_handle = self.session.handler.loop.call_later(2, self._retransmit)

	async def _retransmit(self):
		retr_older = time.time() - RpcChannel.RETR_AFTER_SECS
		for i, (timestamp, data) in self.retr_queue:
			if timestamp > retr_older: break
			await self._transmit_msg(data, self.retr_msg_no + i)
		if len(self.retr_queue) > 0:
			self.retransmit_timeout_handle = self.session.handler.loop.call_later(1, self._retransmit)
		else:
			self.retransmit_timeout_handle = None

	async def _transmit_msg(self, data, pkg_no):
		mtu = self.session.mtu()
		offset = 0
		while len(data) > mtu:
			fdata, data = data[0:mtu], data[mtu:]
			await self.session.send_chan_frame(self.id, RpcChannel.TYPE_MSG_FRAG, pkg_no, offset, fdata)
			offset += len(fdata)

		await self.session.send_chan_frame(self.id, RpcChannel.TYPE_MSG_FIN, pkg_no, offset, data)


CTX=b"rpcNetES"
class EncryptedSession:

	def next_chan_id(self):
		self._next_chan_id += 2
		return self._next_chan_id

	def __init__(self, peer_conn, handler, is_responder, peer_id=None):
		self.state = 0
		self._next_chan_id = 1 if is_responder else 0
		self.handler = handler
		self.preferred_peer_conn = peer_conn
		self.fallback_peer_conns = [ peer_conn ]
		self.peer_public_key = peer_id
		self.kx = pyhy.hydro_kx_xx_client(psk=handler.netkey)
		self.session_id = os.urandom(12)
		self.channels = dict()
		self.timeout_handle = None
		self.send_queue = list()
		self.session_kp = pyhy.hydro_kx_session_keypair("\xAA" * 32, "\xAA" * 32)

	async def send_chan_frame(self, chan_id, flags, msg_no, msg_offset, data):
		plain_frame = struct.pack("!IHHHH", chan_id, flags, msg_no, msg_offset, len(data)) + data
		await self.peer_conn.send(self.encrypt(plain_frame))

	def encrypt(self, plain_frame):
		return pyhy.hydro_secretbox_encrypt(plain_frame, 0, CTX, self.session_kp.tx)

	def decrypt(self, enc_frame):
		return pyhy.hydro_secretbox_decrypt(enc_frame, 0, CTX, self.session_kp.rx)

	async def create_channel(self, proto_handler, **meta):
		id = self.next_chan_id()
		chan = RpcChannel(id, meta=meta, proto_handler=proto_handler, session=self)
		self.channels[id] = chan
		await self.send_chan_frame(id, RpcChannel.TYPE_CREATE,
								   xdrm.dumps(meta))
		return chan

	async def start_kx_initiator(self):
		chan = await self.create_channel(None, proto='rpcnet.Handshake')
		packet1 = self.kx.xx_1()
		await chan.send(packet1)
		packet2 = await chan.recv_pkg()
		(session_kp, packet3, peer_pk) = self.kx.xx_3(packet2, self.handler.keypair)
		self.received_peer_pk(peer_pk)
		await chan.send(packet3)
		self.session_kp = session_kp

	async def start_kx_responder(self, chan):
		packet1 = await chan.recv_pkg()
		packet2 = self.kx.xx_2(packet1, self.handler.keypair)
		await chan.send(packet2)
		packet3 = await chan.recv_pkg()
		(self.session_kp, peer_pk) = self.kx.xx_4(packet3)
		self.received_peer_pk(peer_pk)

	def received_peer_pk(self, peer_pk):
		if self.peer_public_key is not None:
			if self.peer_public_key != peer_pk:
				raise Exception("Invalid peer public key")
		else:
			self.peer_public_key = peer_pk
			self.handler.sessions_by_peer_key[peer_pk] = self

	async def handleFrame(self, enc_frame, sender):
		if self.timeout_handle is not None:
			self.timeout_handle.cancel()
			self.timeout_handle = None
		plain_frame = self.decrypt(enc_frame)
		chan_id, flags, msg_no, msg_offset, data_len = struct.unpack_from("!IHHHH", plain_frame)
		data = plain_frame[12:]

		try:
			chan = self.channels[chan_id]
		except KeyError:
			chan = RpcChannel(id, session=self)
			self.channels[chan_id] = chan

		await chan.handleChunk( flags, msg_no, msg_offset, data)

	def mtu(self):
		return 1024



class RpcTransport:
	def __init__(self, handler):
		self.peers = list()
		self.handler = handler
	async def advertise(self, meta):
		pass
	async def getSelfAddresses(self):
		return []
	async def findPeerConnections(self, peer_id):
		pass

class RpcConnection:
	def __init__(self, rpc_transport, addr):
		self.rpc_transport = rpc_transport
		self.remote_addr = addr
		self.last_timestamp = time.time()

	def handleData(self, session_id, data_item):
		self.rpc_transport.handler.handleData(session_id, data_item, self)

class UdpRpcConnection(RpcConnection):
	async def send(self, buf):
		print("sending %d bytes" % (len(buf)))
		self.rpc_transport.asyncio_transport.sendto(self.session.session_id + buf,
													self.remote_addr)


class UdpSimpleRpcTransport(RpcTransport):
	DUMMY_SESSION = b"\0"*12
	def __init__(self, handler, bindAddress):
		super().__init__(handler)
		self._drain_lock = asyncio.Lock(loop=handler.loop)
		self.bindHost, self.bindPort = UdpSimpleRpcTransport.parseAddress(bindAddress)
		self.connections = dict()
		self.waiting_for_peer = list()

	@staticmethod
	def parseAddress(adr):
		match = re.match("/ip/([^/]+)/udp/(\d+)", adr)
		return (match.group(1), int(match.group(2)))

	async def getSelfAddresses(self):
		return ["/ip/%s/udp/%d"% (ip, self.bindPort) for ip in [self.bindHost]]

	async def advertise(self, meta):
		enc_msg = self.encrypt_adv_msg(meta)
		self.asyncio_transport.sendto(UdpSimpleRpcTransport.DUMMY_SESSION + enc_msg,
									  ("255.255.255.255", self.bindPort))

	def encrypt_adv_msg(self, meta):
		raw_msg = xdrm.dumps(meta)
		signed_msg = self.handler.keypair.sign(raw_msg)
		return pyhy.hydro_secretbox_encrypt(signed_msg, 0, CTX, self.handler.netkey)

	async def findPeerConnections(self, peer_id):
		enc_msg = self.encrypt_adv_msg({"id": self.handler.pk, "find":peer_id})
		self.asyncio_transport.sendto(UdpSimpleRpcTransport.DUMMY_SESSION + enc_msg,
									  ("255.255.255.255", self.bindPort))

	async def connect(self, addr):
		return self.make_connection(UdpSimpleRpcTransport.parseAddress(addr))

	async def run(self):
		transport, protocol = await self.handler.loop.create_datagram_endpoint(lambda: self,
												   local_addr=(self.bindHost,self.bindPort),
								  reuse_address=True, reuse_port=True, allow_broadcast=True)

	def connection_made(self, transport):
		self.asyncio_transport = transport

	def make_connection(self, addr):
		try:
			return self.connections[addr]
		except KeyError:
			self.connections[addr] = UdpRpcConnection(self, addr)

	def datagram_received(self, datagram_bytes, addr):
		session_id, frame = datagram_bytes[0:12], datagram_bytes[12:]
		print('Received %r from %s' % (session_id, addr))
		if session_id == UdpSimpleRpcTransport.DUMMY_SESSION:
			dec_datagram_bytes = pyhy.hydro_secretbox_decrypt(frame, 0, CTX, self.handler.netkey)

			data = sign_unpack(dec_datagram_bytes)
			data['adr'].append("/ip/%s/udp/%d" % addr)
			self.handler.handleAdvertise(data)
		else:
			conn = self.make_connection(addr)
			self.handler.handleData(session_id, frame, conn)
		#
		#print('Send %r to %s' % (message, addr))
		#self.asyncio_transport.sendto(data, addr)

	def error_received(self, exc):
		print("Error in UdpSimpleRpcTransport")
		print(exc)



class ChunkedTlsClientRpcTransport(RpcTransport):
	async def connect(self, destination):
		res = ChunkedTlsClientConnection(self.handler, destination)
		self.handler.loop.ensure_future(res.run_loop())
		return res


class ChunkedTlsClientConnection(RpcConnection):
	def __init__(self, handler, target):
		super().__init__(handler, target)
		self._drain_lock = asyncio.Lock(loop=handler.loop)
		self.targetHost, self.targetPort = target.split(":")

	async def send(self, buf):
		print("sending %d cbor bytes" % (len(buf)))
		self.writer.write(struct.pack("!H", len(buf)) + buf)
		# drain() cannot be called concurrently by multiple coroutines:
		# http://bugs.python.org/issue29930. Remove this lock when no
		# version of Python where this bugs exists is supported anymore.
		with (await self._drain_lock):
			# Handle flow control automatically.
			await self.writer.drain()

	async def run_loop(self):
		try:
			sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='ca.pem')
			sc.load_cert_chain("client.pem")

			self.reader, self.writer = await asyncio.open_connection(
				self.targetHost, self.targetPort, ssl=sc, loop=self.handler.loop)
			# await self.send([1,0,0,"ObjectBroker","add",{"interfaces":list(METHODS.keys()),"alias_index":1}])
			await self.connectionEstablished()
			while True:
				header_buf = await self.reader.readexactly(2)
				if len(header_buf) != 2: break
				frame_len, = struct.unpack("!H", header_buf)
				frame_buf = await self.reader.readexactly(frame_len)
				request = self.encoder.loads(frame_buf)
				print("encoded request received: ", request)
				await self.handleData(self.session.session_id, frame_buf)
			self.writer.close()
			print('Client done')
		except Exception as ex:
			print("Error:", ex)

		print("RPC connection closed")


class KeyPair:
	def __init__(self, raw_keypair=None):
		if raw_keypair is None:
			self.kx_pair = pyhy.hydro_kx_keygen()
			raw_keypair = bytes(self.kx_pair.sk) + bytes(self.kx_pair.pk)
		else:
			self.kx_pair = pyhy.hydro_kx_keypair(raw_keypair[32:64], raw_keypair[0:32])
		self.sign_pk = raw_keypair[32:]
		# https://github.com/jedisct1/libhydrogen/issues/76
		# https://github.com/jedisct1/libsodium/blob/927dfe8e2eaa86160d3ba12a7e3258fbc322909c/src/libsodium/crypto_sign/ed25519/ref10/keypair.c#L18
		sk = bytearray(raw_keypair)
		sk[0] &= 248
		sk[31] &= 127
		sk[31] |= 64
		self.sign_sk = bytes(sk)

	def raw(self):
		return self.sign_sk

	def sign(self, message):
		return pyhy.hydro_sign_create(message, CTX, self.sign_sk) + message

	def sign_pack(self, data):
		data['id'] = self.sign_pk
		return self.sign(xdrm.dumps(data))

def sign_unpack(signed_message):
	msg = signed_message[pyhy.hydro_sign_BYTES:]
	data = xdrm.loads(msg)
	if not pyhy.hydro_sign_verify(signed_message[0:pyhy.hydro_sign_BYTES], msg, CTX, data['id']):
		raise Exception("Signature mismatch")
	return data



async def main():
	from pre_workbench import configs
	params = configs.getValue("rpcnet_opt", {})

	cm = ConnectionManager(**params)
	configs.setValue("rpcnet",cm.saveParams())
	await cm.add_transport(UdpSimpleRpcTransport, "/ip/0.0.0.0/udp/5432")


if __name__ == '__main__':
	asyncio.ensure_future(main())
	asyncio.get_event_loop().run_forever()
