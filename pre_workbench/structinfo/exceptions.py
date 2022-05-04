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

class parse_exception(Exception):
	def __init__(self, context, msg, cause=None):
		self.offset = context.offset()
		self.context_hexdump = context.hexdump_context(self.offset)
		super().__init__(context.get_path() + ": " + msg + "\n" + self.context_hexdump)
		if cause: self.__cause__ = cause
		self.parse_stack = context.stack


class incomplete(parse_exception):
	def __init__(self, context, need, got):
		super().__init__(context, "incomplete: needed %d, got %d bytes" %(need,got))
		self.needed_bytes = need
		self.got_bytes = got


class invalid(parse_exception):
	def __init__(self, context, msg="invalid"):
		super().__init__(context, msg)


class value_not_found(parse_exception):
	def __init__(self, context, msg="value_not_found"):
		super().__init__(context, msg)


class spec_error(parse_exception):
	def __init__(self, context, msg):
		super().__init__(context, "spec_error: "+msg)
		self.offending_desc = context.stack[-1].desc

