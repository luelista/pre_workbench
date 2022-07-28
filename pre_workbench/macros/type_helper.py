from pre_workbench.objects import ByteBuffer, ByteBufferList


def get_supported_macro_types_for_object_type(obj):
	if isinstance(obj, ByteBuffer):
		return ["BYTE_BUFFER","BYTE_ARRAY"]
	elif isinstance(obj, ByteBufferList):
		return ["BYTE_BUFFER_LIST", "BYTE_BUFFER"]
	elif isinstance(obj, str):
		return ["STRING"]
	elif isinstance(obj, (bytes,bytearray)):
		return ["BYTE_ARRAY"]



