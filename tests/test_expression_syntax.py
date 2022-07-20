from lark import Transformer

from pre_workbench.structinfo.expr import Expression

def test_simple():
	check_expr("1+1", "(math (number 1) + (number 1))")
	check_expr("foo>>2", "(math <foo> >> (number 2))")

def test_punktvorstrich():
	check_expr("2+3*4", "(math (number 2) + (math (number 3) * (number 4)))")
	check_expr("2*3+4", "(math (math (number 2) * (number 3)) + (number 4))")
	check_expr("foo<<32 | bar<<16 | baz", "(math (math (math <foo> << (number 32)) | (math <bar> << (number 16))) | <baz>)")

def test_conjunctions():
	check_expr("a == b || c != d || e < f",
			   "(math (math (compare <a> == <b>) || (compare <c> != <d>)) || (compare <e> < <f>))")
	check_expr("a || b && c", "(math (math <a> || <b>) && <c>)")
	check_expr("a && b || c", "(math (math <a> && <b>) || <c>)")
	check_expr("a && (b || c)", "(math <a> && [(math <b> || <c>)])")

def test_arrays():
	check_expr("a[42]", "(array <a> (number 42))")
	check_expr("a.b[42]", "(array (member <a> b) (number 42))")
	check_expr_same("a.b[42]", "(a.b)[42]")
	check_expr("(a + b)[42]", "(array [(math <a> + <b>)] (number 42))")
	check_expr("test(a)[42]", "(array (fun test <a>) (number 42))")
	check_expr("test(a[42])", "(fun test (array <a> (number 42)))")

def check_expr(expr_str, check_str):
	expr = Expression(expr_str=expr_str)
	sl = ShittyLispStringifier().transform(expr.expr_tree)
	assert sl == check_str

def check_expr_same(expr_str, expr_str2):
	expr = Expression(expr_str=expr_str)
	sl = ShittyLispStringifier().transform(expr.expr_tree).replace("[","").replace("]","")
	expr2 = Expression(expr_str=expr_str2)
	sl2 = ShittyLispStringifier().transform(expr2.expr_tree).replace("[","").replace("]","")
	assert sl == sl2

class ShittyLispStringifier(Transformer):
	def __init__(self):
		super().__init__()

	def paren_expr(self, node):
		return "[" + node[0] + "]"

	def anyfield_expr(self, node):
		return "<" + node[0] + ">"

	def __default__(self, data, children, meta):
		return "(" + data.replace("_expr","") + " " + " ".join(children) + ")"
