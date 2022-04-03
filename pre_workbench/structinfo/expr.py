
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
import json
import os.path
import traceback
import logging

from lark import Lark, Transformer

grammar_file = os.path.join(os.path.dirname(__file__), "format_info.lark")
logging.info("grammar_file: %s", grammar_file)
fi_parser = Lark(open(grammar_file), parser="lalr", start=["start","anytype","expression"])


class Evaluator(Transformer):
	def paren_expr(self, s):
		return s[0]

	def string_expr(self, s):
		return json.loads(s[0])

	def number_expr(self, n):
		return float(n[0]) if "." in n[0] else int(n[0], 0)

	null_expr = lambda self, _: None
	true_expr = lambda self, _: True
	false_expr = lambda self, _: False

	def math_expr(self, node):
		if node[1] == "+":
			return node[0] + node[2]
		elif node[1] == "-":
			return node[0] - node[2]
		elif node[1] == "*":
			return node[0] * node[2]
		elif node[1] == "&":
			return node[0] & node[2]
		elif node[1] == "|":
			return node[0] | node[2]
		elif node[1] == "^":
			return node[0] ^ node[2]
		elif node[1] == "<<":
			return node[0] << node[2]
		elif node[1] == ">>":
			return node[0] >> node[2]
		elif node[1] == "/":
			if isinstance(node[0], dict): return node[0][node[1]]
			return node[0] / node[2]
		elif node[1] == "||":
			return node[0] or node[2]
		elif node[1] == "&&":
			return node[0] and node[2]

	def compare_expr(self, node):
		if node[1] == "==":
			return node[0] == node[2]
		elif node[1] == "!=":
			return node[0] != node[2]
		elif node[1] == "<":
			return node[0] < node[2]
		elif node[1] == ">":
			return node[0] > node[2]
		elif node[1] == ">=":
			return node[0] >= node[2]
		elif node[1] == "<=":
			return node[0] <= node[2]

	def bool_expr(self, node):
		if node[1] == "||":
			return node[0] or node[2]
		elif node[1] == "&&":
			return node[0] and node[2]

	def fun_expr(self, node):
		name, param = node
		if name == "hex":
			if type(param) in (bytes, bytearray):
				return binascii.hexlify(param).decode('ascii')
			else:
				return hex(param)
		elif name == "snip":
			return str(param)[:32]
		else:
			raise Exception("Call to unknown function '"+name+"'")

class ParseContextEvaluator(Evaluator):
	def __init__(self, parse_context):
		super().__init__()
		self.parse_context = parse_context

	def hierarchy_expr(self, node):
		#print("hierarchy_expr", node, self.parse_context.stack[-len(node[0])][1])
		return self.parse_context.stack[-len(node[0])].value

	def array_expr(self, node):
		#print("array_expr", node)
		return self.parse_context.unpack_value(node[0][node[1]])

	def member_expr(self, node):
		#print("member_expr", node)
		try:
			return self.parse_context.unpack_value(node[0][node[1]])
		except KeyError as e:
			raise Exception("item has no member named "+str(node[1]))

	def anyfield_expr(self, node):
		id = node[0]
		for i in range(len(self.parse_context.stack)-1, -1, -1):
			frame = self.parse_context.stack[i]
			if frame.value is not None and id in frame.value:
				return self.parse_context.unpack_value(frame.value[id])
		raise Exception("field "+id+" not found")

	def param_expr(self, node):
		return self.parse_context.get_param(node[0])

	def fun_expr(self, node):
		name, param = node
		if name == "pad":
			len = self.parse_context.top_length(-2)
			if len % param == 0:
				return 0
			else:
				return param - (len % param)
		else:
			super().fun_expr(node)

def generic_unpack_value(packed_value):
	while hasattr(packed_value, 'value'):
		packed_value = packed_value.value
	return packed_value

class ByteBufferEvaluator(Evaluator):
	def __init__(self, bbuf):
		super().__init__()
		self.bbuf = bbuf

	def hierarchy_expr(self, node):
		raise NotImplemented

	def array_expr(self, node):
		#print("array_expr", node)
		return generic_unpack_value(node[0][node[1]])

	def member_expr(self, node):
		#print("member_expr", node)
		try:
			return generic_unpack_value(node[0][node[1]])
		except KeyError as e:
			raise Exception("item has no member named "+str(node[1]))

	def anyfield_expr(self, node):
		id = node[0]
		if id == "payload":
			return self.bbuf.buffer
		if id == "fields":
			return self.bbuf.fields
		frame = generic_unpack_value(self.bbuf.fi_tree)
		#print(frame)
		if frame is not None and id in frame:
			return generic_unpack_value(frame[id])
		raise Exception("field "+id+" not found")

	def param_expr(self, node):
		return self.bbuf.metadata[node[0]]



class DictEvaluator(Evaluator):
	def __init__(self, dic):
		super().__init__()
		self.dic = dic

	def hierarchy_expr(self, node):
		raise NotImplemented

	def array_expr(self, node):
		#print("array_expr", node)
		return node[0][node[1]]

	def member_expr(self, node):
		#print("member_expr", node)
		try:
			return node[0][node[1]]
		except KeyError as e:
			raise Exception("item has no member named "+str(node[1]))

	def anyfield_expr(self, node):
		id = node[0]
		frame = self.dic
		if frame is not None and id in frame:
			return frame[id]
		raise Exception("field "+id+" not found")

	def param_expr(self, node):
		return self.bbuf.metadata[node[0]]


class Stringifier(Transformer):
	def __init__(self):
		super().__init__()

	def string_expr(self, s):
		return json.dumps(s[0])

	def number_expr(self, n):
		return str(n[0])

	null_expr = lambda self, _: "null"
	true_expr = lambda self, _: "true"
	false_expr = lambda self, _: "false"

	def math_expr(self, node):
		return " ".join(node)

	def compare_expr(self, node):
		return " ".join(node)

	def bool_expr(self, node):
		return " ".join(node)

	def hierarchy_expr(self, node):
		return node[0]

	def member_expr(self, node):
		return node[0] + "." + node[1]

	def array_expr(self, node):
		return node[0] + "[" + node[1] + "]"

	def anyfield_expr(self, node):
		return node[0]

	def param_expr(self, node):
		return "$" + node[0]

	def paren_expr(self, node):
		return "(" + node[0] + ")"

	def fun_expr(self, node):
		return node[0] + "(" + node[1] + ")"


class CCodeGenerator(Transformer):
	def __init__(self):
		super().__init__()

	def string_expr(self, s):
		return json.dumps(s[0])

	def number_expr(self, n):
		return str(n[0])

	null_expr = lambda self, _: "NULL"
	true_expr = lambda self, _: "TRUE"
	false_expr = lambda self, _: "FALSE"

	def math_expr(self, node):
		return " ".join(node)

	def compare_expr(self, node):
		return " ".join(node)

	def hierarchy_expr(self, node):
		return node[0]

	def member_expr(self, node):
		return "get_member(" + node[0] + ", \"" + node[1] + "\")"

	def array_expr(self, node):
		return "get_array_item(" + node[0] + ", " + node[1] + ")"

	def anyfield_expr(self, node):
		return "find_by_name(\"" + node[0] + "\")"

	def param_expr(self, node):
		return "get_param(\"" + node[0] + "\")"

	def paren_expr(self, node):
		return "(" + node[0] + ")"


def deserialize_expr(expr):
	if isinstance(expr, Expression): return expr
	return Expression(expr_str=expr)


class Expression:
	def __init__(self, expr_str=None, expr_tree=None):
		if expr_str:
			self.expr_str = expr_str
			try:
				self.expr_tree = fi_parser.parse(self.expr_str, start="expression")
			except Exception as e:
				raise Exception("Failed to parse expression '"+expr_str+"': "+str(e)) from e
		elif expr_tree:
			self.expr_tree = expr_tree
			self.expr_str = Stringifier().transform(expr_tree)

	def serialize(self):
		return self.expr_str
	def to_text(self, indent=0, refs=None):
		return "("+self.expr_str+")"

	def evaluate(self, parse_context):
		try:
			return ParseContextEvaluator(parse_context).transform(self.expr_tree)
		except Exception as e:
			#logging.exception("Failed to eval expr_str: %s", self.expr_str)
			#logging.warning("expr_tree pretty: %s", self.expr_tree.pretty())
			raise Exception("Failed to evaluate expression '"+self.expr_str+"' ("+type(e).__name__+"): "+str(e)) from e

	def evaluate_bbuf(self, bbuf):
		try:
			return ByteBufferEvaluator(bbuf).transform(self.expr_tree)
		except Exception as e:
			#logging.exception("Failed to eval expr_str on bbuf: %s", self.expr_str)
			#logging.warning("expr_tree pretty: %s", self.expr_tree.pretty())
			raise Exception("Failed to evaluate expression '"+self.expr_str+"' ("+type(e).__name__+"): "+str(e)) from e

	def evaluate_dict(self, dic):
		try:
			return DictEvaluator(dic).transform(self.expr_tree)
		except Exception as e:
			#logging.exception("Failed to eval expr_str on dict: %s", self.expr_str)
			#logging.warning("expr_tree pretty: %s", self.expr_tree.pretty())
			raise Exception("Failed to evaluate expression '"+self.expr_str+"' ("+type(e).__name__+"): "+str(e)) from e


if __name__ == "__main__":
	from pre_workbench import ParseContext
	import sys
	e = Expression(sys.argv[1])
	print(e.expr_tree.pretty())
	pc = ParseContext()
	pc.push(None, {"zzz":999})
	pc.push(None, {"yyy":888})
	pc.push(None, {"a":1,"b":2,"dd":{"x":5}})
	print("Result:",e.evaluate(pc))

