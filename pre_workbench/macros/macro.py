import hashlib
import json
import logging
import traceback
from glob import glob
import os.path
from typing import List, Optional

import yaml
from PyQt5.QtWidgets import QMessageBox

from pre_workbench.app import MainWindow
from pre_workbench.configs import SettingsField
from pre_workbench.controls.genericwidgets import showSettingsDlg
from pre_workbench.structinfo import xdrm


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

	def execute(self, input, params=None):
		hash = hashlib.sha256(self.code.encode('utf-8')).digest()
		from pre_workbench import configs
		if hash not in configs.getValue("TrustedMacroHashes", []):
			QMessageBox.warning(MainWindow, "Refusing to Run Untrusted Macro", "This macro is untrusted. \n\nTo mark it as trusted, open it in the macro editor, review the code, and then save it.\n\nBe careful: Macros run without any additional sandboxing in the context of this applications, and may write to all your user files.")
			return None
		if params is None and len(self.options) > 0:
			params = showSettingsDlg(self.getSettingsFields(), None, "Run Macro \"" + self.name + "\"")
			if not params: return None
		try:
			from pre_workbench.macros import macroenv
			locals = {key: getattr(macroenv, key) for key in macroenv.__all__}
			if params: locals.update(params)
			locals['input'] = input
			exec(self.code, globals(), locals)
			return locals.get('output')
		except:
			QMessageBox.warning(MainWindow, "Macro Execution Failed", traceback.format_exc())

class SysMacroContainer:
	def __init__(self):
		searchPath = os.path.join(os.path.dirname(__file__), "sys_macros/*.macro.yml")
		logging.debug("Loading sys-macros from "+searchPath)
		self.macros = [self._loadMacro(filename) for filename in glob(searchPath)]
		self.containerId = "BUILTIN"
		self.containerTitle = "Bundled with pre_workbench"

	def _loadMacro(self, filename):
		with open(filename, "r") as f:
			data = yaml.safe_load(f)
		with open(filename.replace(".macro.yml", ".py"), "r") as f:
			code = f.read()
		return Macro(self, os.path.basename(filename.replace(".macro.yml", "")), data["input_type"], data["output_type"], code, data["options"], data["metadata"], None)

	def getMacroNames(self):
		return [macro.name for macro in self.macros]

	def getMacroNamesByInputType(self, inputType):
		return [macro.name for macro in self.macros if macro.input_type == inputType]

	def getMacro(self, name):
		return next(macro for macro in self.macros if macro.name == name)

	@property
	def macrosEditable(self):
		return False
