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

import uuid

from .. import typeeditor
from . import xdrm, deserialize_fi

def bin_serialize_fi(self):
	return xdrm.dumps([uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07"), "FormatInfoFile", self.serialize()], magic=typeeditor.FILE_MAGIC)

def bin_deserialize_fi(bin):
	iid, typename, data = xdrm.loads(bin, magic=typeeditor.FILE_MAGIC)
	if iid != uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07") or typename != "FormatInfoFile":
		raise Exception("Invalid file format (got iid=%r typename=%r)"%(iid,typename))
	return deserialize_fi(data)


def recursive_serialize(obj):
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