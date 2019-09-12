from lark import Lark, Transformer

from structinfo import FixedFieldFI, VarByteFieldFI, VariantStructFI, StructFI, RepeatStructFI, SwitchFI, NamedFI

fi_parser = Lark(open("format_info.lark"))

def parse_fi(txt):
	ast = fi_parser.parse(txt)
	print(ast.pretty())

	trans = MainTrans()
	trans.load_definitions(ast)

	fi = trans.inflate(trans.main_name)
	return fi

builtin_fixedfields = {v: k for k, v in FixedFieldFI.struct_format_alias.items()}
def make_builtin(name, params):
	if name in builtin_fixedfields:
		return FixedFieldFI(format=builtin_fixedfields[name], **params)
	if name == "bytes":
		return VarByteFieldFI(**params)
	return None

class MainTrans(Transformer):
	def __init__(self):
		super().__init__()
		self.definitions = {}
		self.instances = {}
		self.named_fi_to_fill = list()

	def load_definitions(self, ast):
		for definition in ast.children:
			self.definitions[definition.children[0]] = definition.children[1]
		self.main_name = ast.children[0].children[0]

	def inflate(self, name):
		item = self._inflate_internal(name)
		for nfi in self.named_fi_to_fill:
			nfi.ref = self._inflate_internal(nfi.def_name)
		self.named_fi_to_fill = list()
		return item

	def _inflate_internal(self, name):
		if not name in self.instances:
			self.instances[name] = self.transform(self.definitions[name])
			self.instances[name].params['def_name'] = name
		return self.instances[name]


	def string(self, s):
		return s[0][1:-1]
	def number(self, n):
		return float(n[0]) if "." in n[0] else int(n[0])

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
		item = NamedFI(def_name=name, **params)
		self.named_fi_to_fill.append(item)
		return item

	def structfi(self, node):
		params, children = node
		return StructFI(children=children, **params)

	def variantfi(self, node):
		params, children = node
		return VariantStructFI(children=children, **params)

	def repeatfi(self, node):
		params, child = node
		return RepeatStructFI(children=child, **params)

	def switchfi(self, node):
		expr, params, cases = node
		return SwitchFI(expr=expr, children=cases, **params)



if __name__ == "__main__":
	import sys
	txt = open(sys.argv[1], "r").read()
	fi = parse_fi(txt)
	print(fi)
	print(fi.to_text())

