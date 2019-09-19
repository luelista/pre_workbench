import json

from lark import Lark, Transformer


fi_expr_parser = Lark(open("format_info.lark"), start="expression", parser="lalr")

class Evaluator(Transformer):
	def __init__(self, parse_context):
		super().__init__()
		self.parse_context = parse_context

	def paren_expr(self, s):
		return s[0]

	def string_expr(self, s):
		return json.loads(s)

	def number_expr(self, n):
		return float(n[0]) if "." in n[0] else int(n[0], 0)

	null_expr = lambda self, _: None
	true_expr = lambda self, _: True
	false_expr = lambda self, _: False

	def math_expr(self, node):
		print(node)
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

	def hierarchy_expr(self, node):
		print("hierarchy_expr", node, self.parse_context.stack[-len(node[0])][1])
		return self.parse_context.stack[-len(node[0])][1]

	def array_expr(self, node):
		print("array_expr", node)
		return self.parse_context.unpack_value(node[0][node[1]])

	def member_expr(self, node):
		print("member_expr", node)
		return self.parse_context.unpack_value(node[0][node[1]])

	def anyfield_expr(self, node):
		id = node[0]
		for i in range(len(self.parse_context.stack)-1, -1, -1):
			frame = self.parse_context.stack[i]
			if frame[1] is not None and id in frame[1]:
				return self.parse_context.unpack_value(frame[1][id])
		raise Exception("field "+id+" not found")

	def param_expr(self, node):
		return self.parse_context.get_param(node[0])


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


def deserialize_expr(expr):
	if isinstance(expr, Expression): return expr
	return Expression(expr_str=expr)

class Expression:
	def __init__(self, expr_str=None, expr_tree=None):
		if expr_str:
			self.expr_str = expr_str
			try:
				self.expr_tree = fi_expr_parser.parse(self.expr_str)
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
			return Evaluator(parse_context).transform(self.expr_tree)
		except Exception as e:
			print(self.expr_str)
			print(self.expr_tree.pretty())
			raise Exception("Failed to evaluate expression '"+self.expr_str+"': "+str(e)) from e



if __name__ == "__main__":
	from structinfo import ParseContext
	import sys
	e = Expression(sys.argv[1])
	print(e.expr_tree.pretty())
	pc = ParseContext()
	pc.push(None, {"zzz":999})
	pc.push(None, {"yyy":888})
	pc.push(None, {"a":1,"b":2,"dd":{"x":5}})
	print("Result:",e.evaluate(pc))

