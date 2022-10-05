import hashlib
import logging
import traceback
from collections import defaultdict, namedtuple
from glob import glob
import os.path
from typing import List, Optional

import yaml
from PyQt5.QtWidgets import QMessageBox

from pre_workbench.app import MainWindow
from pre_workbench.configs import SettingsField
from pre_workbench.controls.genericwidgets import showSettingsDlg

last_params = defaultdict(dict)

MacroListItem = namedtuple('MacroListItem', ['name', 'input_type'])

class Macro:
	name: str
	code: str
	options: List[dict]
	input_type: str
	output_type: str
	metadata: dict
	_rowid: Optional[int]
	container: object

	TYPE_BYTE_BUFFER = "BYTE_BUFFER"
	TYPE_BYTE_BUFFER_LIST = "BYTE_BUFFER_LIST"
	TYPE_STRING = "STRING"
	TYPE_BYTE_ARRAY = "BYTE_ARRAY"
	TYPE_DATA_SOURCE = "DATA_SOURCE"
	TYPE_SELECTION_HEURISTIC = "SELECTION_HEURISTIC"
	TYPE_NONE = "NONE"
	TYPES = [
		TYPE_NONE,
		TYPE_BYTE_BUFFER,
		TYPE_BYTE_BUFFER_LIST,
		TYPE_STRING,
		TYPE_BYTE_ARRAY,
		TYPE_DATA_SOURCE,
		TYPE_SELECTION_HEURISTIC,
	]

	def __init__(self, container, name: str, input_type: str, output_type: str, code: str, options: List[dict], metadata: dict, rowid: Optional[int]):
		self.container = container
		self.name = name
		self.input_type = input_type
		self.output_type = output_type
		self.code = code
		self.options = options
		self.metadata = metadata
		self._rowid = rowid

	def getSettingsFields(self):
		return [SettingsField(**kw) for kw in self.options]

	@property
	def isTrusted(self):
		from pre_workbench import configs
		hash = hashlib.sha256(self.code.encode('utf-8')).digest()
		return hash in configs.getValue("TrustedMacroHashes", [])

	def execute(self, input, params=None):
		if not self.isTrusted:
			QMessageBox.warning(MainWindow, "Refusing to Run Untrusted Macro", "This macro is untrusted. \n\nTo mark it as trusted, open it in the macro editor, review the code, and then save it.\n\nBe careful: Macros run without any additional sandboxing in the context of this applications, and may write to all your user files.")
			return None
		if params is None and len(self.options) > 0:
			params = showSettingsDlg(self.getSettingsFields(), last_params[self.name], "Run Macro \"" + self.name + "\"")
			if not params: return None
			last_params[self.name] = params
		try:
			from pre_workbench.macros import macroenv
			locals = {key: getattr(macroenv, key) for key in macroenv.__all__}
			if params: locals.update(params)
			locals['input'] = input
			exec(self.code, locals, locals)
			return locals.get('output')
		except:
			QMessageBox.warning(MainWindow, "Macro Execution Failed", traceback.format_exc())

	# def _coerce_input_type(self, input):
	# 	if self.input_type == Macro.TYPE_BYTE_BUFFER:
	# 		if type(input).__name__ == 'ByteBuffer':
	# 			return input
	# 		elif isinstance(input, (bytes, bytearray)):
	# 			return ByteBuffer(input)
	# 	elif self.input_type == Macro.TYPE_BYTE_BUFFER_LIST:
	# 		if type(input).__name__ == 'ByteBufferList':
	# 			return input
	# 		elif isinstance(input, list)
	# 	raise TypeError('Invalid input of type '+type(input).__name__+' to macro expecting '+self.input_type)


class SysMacroContainer:
	def __init__(self):
		searchPath = os.path.join(os.path.dirname(__file__), "sys_macros/*.macro.yml")
		logging.debug("Loading sys-macros from "+searchPath)
		self.macros = [self._loadMacro(filename) for filename in glob(searchPath)]
		self.containerId = "BUILTIN"
		self.containerTitle = "Bundled with pre_workbench"

	def _loadMacro(self, filename: str) -> Macro:
		with open(filename, "r") as f:
			data = yaml.safe_load(f)
		return Macro(self, os.path.basename(filename.replace(".macro.yml", "")), data["input_type"], data["output_type"], data["code"], data["options"], data["metadata"], None)

	def getMacros(self) -> List[MacroListItem]:
		return [MacroListItem(macro.name, macro.input_type) for macro in self.macros]

	def getMacroNamesByInputTypes(self, inputTypes: List[str]) -> List[str]:
		return [macro.name for macro in self.macros if macro.input_type in inputTypes]

	def getMacro(self, name: str) -> Macro:
		return next(macro for macro in self.macros if macro.name == name)

	@property
	def macrosEditable(self) -> bool:
		return False
