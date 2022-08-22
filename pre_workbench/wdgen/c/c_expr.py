import json

from lark import Transformer


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

