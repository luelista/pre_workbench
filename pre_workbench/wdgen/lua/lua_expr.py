
from lark import Transformer


def to_lua_expr(expr):
	return WDExprStringifier().transform(expr.expr_tree)


class WDExprStringifier(Transformer):
	def __init__(self):
		super().__init__()

	def string_expr(self, s):
		return s[0]

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
		return "fval['" + node[0] + "']"

	def param_expr(self, node):
		return "$" + node[0]

	def paren_expr(self, node):
		return "(" + node[0] + ")"

	def fun_expr(self, node):
		return node[0] + "(" + node[1] + ")"

