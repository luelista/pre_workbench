
class TypeRegistry:
	def __init__(self):
		self.types = list()
	def register(self, **meta):
		def wrapper(typ):
			meta["name"] = typ.__name__
			self.types.append([typ, meta])
			return typ
		return wrapper
	def find(self, **checkForMeta):
		for typ, meta in self.types:
			match = True
			for key, value in checkForMeta.items():
				if meta.get(key) != value:
					if type(meta.get(key)) == list and value in meta.get(key): continue
					match = False
					break
			if match:
				return typ
		return None
	def getSelectList(self, displayMeta):
		return [("", "")] + [(typ.__name__, meta[displayMeta]) for typ, meta in self.types]


WindowTypes = TypeRegistry()
DataWidgetTypes = TypeRegistry()
