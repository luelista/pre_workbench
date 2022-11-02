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
import binascii

from pre_workbench.structinfo import ExprFunctions

ExprFunctions.register()(str)
ExprFunctions.register()(len)


@ExprFunctions.register()
def dec(i):
	return str(i)


@ExprFunctions.register()
def hex(i):
	if isinstance(i, (bytes, bytearray)):
		return binascii.hexlify(i, ":").decode('ascii')
	else:
		return "0x%x" % i


@ExprFunctions.register()
def dotted_quad(b):
	return ".".join("%d" % i for i in b)


@ExprFunctions.register()
def ip6(b):
	from ipaddress import IPv6Address
	return str(IPv6Address(b))


@ExprFunctions.register()
def getrange(param, key):
	return param[key]

@ExprFunctions.register()
def snip(param):
	return str(param)[:32]

@ExprFunctions.register()
def iif(cond, true_val, false_val):
	return true_val if cond else false_val

@ExprFunctions.register()
def choice(cond, *vals):
	for i in range(0, len(vals), 2):
		if vals[i] == cond: return vals[i+1]
	return ""


