import json

from pre_workbench.objects import ByteBuffer, ByteBufferList, ReloadRequired

with open(fileName, "r") as file:
	lst = json.load(file)

plist = ByteBufferList()
for item in lst:
	payload = re.sub("\s", "", row[payload_key])
	payload_decoded = decoder(payload)
	plist.add(ByteBuffer(payload_decoded, metadata = item))

	output = plist

