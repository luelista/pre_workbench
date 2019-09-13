
from lark import Lark, Transformer


fi_expr_parser = Lark(open("format_info.lark"), start="expression")

class Evaluator(Transformer):
	def __init__(self, parse_context):
		super().__init__()
		self.parse_context = parse_context

	def string(self, s):
		return s[0][1:-1]

	def number(self, n):
		return float(n[0]) if "." in n[0] else int(n[0], 0)

	null = lambda self, _: None
	true = lambda self, _: True
	false = lambda self, _: False

	def math_expr(self, node):
		print(node)
		if node[1] == "+":
			return node[0] + node[2]
		elif node[1] == "-":
			return node[0] - node[2]
		elif node[1] == "*":
			return node[0] * node[2]
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

	def anyfield_expr(self, node):
		id = node[0]
		for i in range(len(self.parse_context.stack)-1, -1, -1):
			frame = self.parse_context.stack[i]
			if frame[1] is not None and id in frame[1]:
				return self.parse_context.unpack_value(frame[1][id])
		raise Exception("field "+id+" not found")

	def param_expr(self, node):
		return self.parse_context.get_param(node[0])


class Expression:
	def __init__(self, expr_str):
		self.expr_str = expr_str
		try:
			self.expr_tree = fi_expr_parser.parse(self.expr_str)
		except Exception as e:
			raise Exception("Failed to parse expression '"+expr_str+"': "+str(e)) from e

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

