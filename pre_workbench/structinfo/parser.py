
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
import json

from lark import Transformer

from pre_workbench.structinfo.format_info import VariantStructFI, StructFI, RepeatStructFI, SwitchFI, NamedFI, \
	FormatInfo, UnionFI, FieldFI, builtinTypes, BitStructFI
from pre_workbench.structinfo.expr import Expression, fi_parser


def make_builtin(name, params):
	if name in builtinTypes:
		return FormatInfo(typeRef=FieldFI, params={"format_type": name, **params})
	else:
		return None


def parse_definition(txt, start="anytype"):
	ast = fi_parser.parse(txt, start=start)

	return transformer.transform(ast)


def parse_definition_map_into_container(txt, container, start="start"):
	ast = fi_parser.parse(txt, start=start)

	for definition in ast.children:
		container.definitions[definition.children[0]] = transformer.transform(definition.children[1])
	container.main_name = ast.children[0].children[0]


class MainTrans(Transformer):
	def __init__(self):
		super().__init__()

	start = dict

	def string(self, s):
		return json.loads(s[0])

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
	bitstructfields = list
	bitstructfield = tuple
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

	def unionfi(self, node):
		params, children = node
		params['children'] = children
		return FormatInfo(typeRef=UnionFI, params=params)

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

	def bitstructfi(self, node):
		params, children = node
		params['children'] = children
		return FormatInfo(typeRef=BitStructFI, params=params)

	def expr_value(self, node):
		return Expression(expr_tree=node[0])

transformer = MainTrans()

