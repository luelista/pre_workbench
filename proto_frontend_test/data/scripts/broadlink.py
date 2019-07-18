
import scapy.contrib.tzsp
conf.l2types.register(0x80, scapy.contrib.tzsp.TZSP)

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from binascii import unhexlify

default_key = unhexlify("097628343fe99e23765c1513accf8b02")
default_iv = unhexlify("562e17996d093d28ddb3ba695a2e6f58")
other_key = unhexlify('a0f55f28d768d6170ddc4c077ac23966')

class BL(Packet):
	fields_desc = [
		XLongField("magic1",0),
		LEIntField("timezone",0),
		LEShortField("year",0),
		ByteField("seconds",0),
		ByteField("minutes",0),
		ByteField("hours",0),
		ByteField("dow",0),
		ByteField("day",0),
		ByteField("month",0),
		LEIntField("reserved_zero",0),
		IPField("local_ip",None),
		LEShortField("src_port",0),
		ShortField("reserved",0),
		XLEShortField("checksum",0),
		LEShortField("reserved_zero2",0),
		XLEShortField("device_type",0),
		LEShortEnumField("cmd_type",0, {
			0x0006: "NetworkDiscovery",
			0x0014: "DeviceSetup",
			0x0065: "Authorization",
			0x006a: "LearningMode",
			0x03e9: "AuthorizationResponse",
		}),
		LEShortField("packet_number",0),
		MACField("local_mac",None),
		XLEIntField("local_device_id",0),
		XLEShortField("payload_checksum",0),
		XLEShortField("reserved_zero3",0),
	]

	def post_dissect(self, s):
		print("test",len(s))
		try:
			print("Type: %04x PayLen: %d"%(self.cmd_type,len(s)))
			backend = default_backend()
			key = other_key
			if self.cmd_type == 0x0065 or self.cmd_type == 0x03e9:
				key = default_key
			cipher = Cipher(algorithms.AES(key), modes.CBC(default_iv), backend=backend)
			decryptor = cipher.decryptor()

			pay = decryptor.update(s) + decryptor.finalize()
			if bl_cksum(pay) == self.payload_checksum:
				print("Checksum valid")
				self.fields["checksum_valid"] = "true"
			else:
				print("Checksum invalid %x != %x"%(bl_cksum(pay) ,self.payload_checksum))
				self.fields["checksum_valid"] = "false"
			return pay
		except Exception as e:
			print(e)
			return s
	#def extract_padding(self, p):
	#	print("Type: %04x PayLen: %d"%(self.cmd_type,len(p)))
	#		
	#	#print(p, pay)
	#	return pay, ""

class BL_Enc_Packet(Packet):
	key = default_key

class BL_Auth(BL_Enc_Packet):
	key = other_key
	fields_desc = [
		XLEIntField("reserved_zero",0),
		StrFixedLenField("imei",None,15),
		ByteField("reserved_one",1),
		StrFixedLenField("reserved_zero2",None,0x2c-0x14+1),
		ByteField("reserved_one2",1),
		ByteField("device_name",0x7f-0x30+1),
	]
class BL_AuthResponse(BL_Enc_Packet):
	key = other_key
	fields_desc = [
		XLEIntField("device_id",0),
		StrFixedLenField("device_encryption_key",None,16),
	]

def bl_cksum(payload):
	checksum = 0xbeaf
	for i in range(len(payload)):
		checksum += payload[i]
		checksum = checksum & 0xffff
	return checksum


bind_layers(UDP, BL, dport=80)
bind_layers(UDP, BL, sport=80)
bind_layers(BL, BL_Auth, cmd_type=0x0065)
bind_layers(BL, BL_AuthResponse, cmd_type=0x03e9)
bind_layers(BL, BL_Enc_Packet)
print("-----")
