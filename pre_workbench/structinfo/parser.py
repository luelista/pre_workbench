
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

from lark import Transformer

from . import FixedFieldFI, VarByteFieldFI, VariantStructFI, StructFI, RepeatStructFI, SwitchFI, NamedFI, \
	FormatInfo
from .expr import Expression

builtinTypes = {"fixed": FixedFieldFI, "bytes": VarByteFieldFI}
def make_builtin(name, params):
	try:
		t = builtinTypes[name]
	except KeyError:
		return None
	return FormatInfo(typeRef=t, params=params)


class MainTrans(Transformer):
	def __init__(self, container):
		super().__init__()
		self.container = container

	def load_definitions(self, ast):
		for definition in ast.children:
			self.container.definitions[definition.children[0]] = self.transform(definition.children[1])
		self.container.main_name = ast.children[0].children[0]

	start = dict


	def string(self, s):
		return s[0][1:-1]
	def number(self, n):
		return float(n[0]) if "." in n[0] else int(n[0], 0)

	list = list
	pair = tuple
	parampair = tuple
	dict = dict
	params = dict
	moreparams = dict
	field = tuple
	variantchildren = list
	structfields = list
	switchcases = list
	switchcase = tuple

	def explicitnamedfi(self, node):
		return node[0]

	null = lambda self, _: None
	true = lambda self, _: True
	false = lambda self, _: False

	def namedfi(self, node):
		name, params = node
		item = make_builtin(name, params)
		if item: return item
		params['ref_name'] = name
		item = FormatInfo(typeRef=NamedFI, params=params)
		return item

	def structfi(self, node):
		params, children = node
		params['children'] = children
		return FormatInfo(typeRef=StructFI, params=params)

	def variantfi(self, node):
		params, children = node
		params['children'] = children
		return FormatInfo(typeRef=VariantStructFI, params=params)

	def repeatfi(self, node):
		params, child = node
		params['children'] = child
		return FormatInfo(typeRef=RepeatStructFI, params=params)

	def switchfi(self, node):
		expr, params, cases = node
		params['expr'] = expr
		params['children'] = cases
		return FormatInfo(typeRef=SwitchFI, params=params)

	def expr_value(self, node):
		return Expression(expr_tree=node[0])



