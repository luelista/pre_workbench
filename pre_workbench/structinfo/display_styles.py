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

def dec(i):
	return str(i)

def hex(i):
	if isinstance(i, (bytes, bytearray)):
		return ":".join("%02x" % a for a in i)
	else:
		return "0x%x" % i

def dotted_quad(b):
	return ".".join("%d" % i for i in b)

def ip6(b):
	return ":".join("%x" % i for i in b)


