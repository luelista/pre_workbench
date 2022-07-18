import hashlib
import json
import traceback
from glob import glob
import os.path
from typing import List, Optional

from PyQt5.QtWidgets import QMessageBox

from pre_workbench.app import MainWindow
from pre_workbench.configs import SettingsField
from pre_workbench.structinfo import xdrm


class Macro:
	name: str
	code: str
	options: List[SettingsField]
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

	def __init__(self, container, name: str, input_type: str, output_type: str, code: str, options: bytes, metadata: bytes, rowid: Optional[int]):
		self.container = container
		self.name = name
		self.input_type = input_type
		self.output_type = output_type
		self.code = code
		self.options = options if isinstance(options, list) else xdrm.loads(options)
		self.metadata = metadata if isinstance(metadata, dict) else xdrm.loads(metadata)
		self._rowid = rowid

	def execute(self, input):
		hash = hashlib.sha256(self.code.encode('utf-8')).digest()
		from pre_workbench import configs
		if hash not in configs.getValue("TrustedMacroHashes", []):
			QMessageBox.warning(MainWindow, "Refusing to Run Untrusted Macro", "This macro is untrusted. \n\nTo mark it as trusted, open it in the macro editor, review the code, and then save it.\n\nBe careful: Macros run without any additional sandboxing in the context of this applications, and may write to all your user files.")
			return None
		try:
			from pre_workbench.macros import macroenv
			locals = {key: getattr(macroenv, key) for key in macroenv.__all__}
			locals['input'] = input
			exec(self.code, globals(), locals)
			return locals.get('output')
		except:
			QMessageBox.warning(MainWindow, "Macro Execution Failed", traceback.format_exc())

class SysMacroContainer:
	def __init__(self):
		searchPath = os.path.join(os.path.dirname(__file__), "sys_macros/*.macro.json")
		print(searchPath)
		self.macros = [self._loadMacro(filename) for filename in glob(searchPath)]

	def _loadMacro(self, filename):
		with open(filename, "r") as f:
			data = json.load(f)
		with open(filename.replace(".macro.json", ".py"), "r") as f:
			code = f.read()
		return Macro(self, os.path.basename(filename.replace(".macro.json", "")), data["input_type"], data["output_type"], code, data["options"], data["metadata"], None)

	def getMacroNames(self):
		return [macro.name for macro in self.macros]

	def getMacroNamesByInputType(self, inputType):
		return [macro.name for macro in self.macros if macro.input_type == inputType]

	def getMacro(self, name):
		return next(macro for macro in self.macros if macro.name == name)

	@property
	def macrosEditable(self):
		return False
