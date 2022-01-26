# PRE Workbench
# Copyright (C) 2022 Mira Weller
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

import uuid

from pre_workbench.structinfo import xdrm

FILE_MAGIC = b"\xde\xca\xf9\x30"
IFACE_UUID = uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07")


def bin_serialize_fi(self):
	return xdrm.dumps([IFACE_UUID, "FormatInfoFile", self.serialize()], magic=FILE_MAGIC)

def bin_deserialize_fi(bin):
	iid, typename, data = xdrm.loads(bin, magic=FILE_MAGIC)
	if iid != IFACE_UUID or typename != "FormatInfoFile":
		raise Exception("Invalid file format (got iid=%r typename=%r)"%(iid,typename))
	return deserialize_fi(data)


def recursive_serialize(obj):
	from pre_workbench.structinfo.format_info import FormatInfo
	if isinstance(obj, dict):
		return {k:recursive_serialize(v) for k,v in obj.items()}
	elif isinstance(obj, list):
		return [recursive_serialize(v) for v in obj]
	elif isinstance(obj, tuple):
		return tuple(recursive_serialize(v) for v in obj)
	elif isinstance(obj, FormatInfo):
		return obj.serialize()
	else:
		return obj

def deserialize_fi(data):
	from pre_workbench.structinfo.format_info import FormatInfo
	if type(data) == list and len(data) == 2:
		return FormatInfo(data)
	else:
		return data

