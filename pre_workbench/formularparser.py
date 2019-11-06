import math
import re
import traceback
import xml.parsers.expat
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import QWidget, QTextBrowser, QTabWidget, QFrame, QLabel, QLineEdit

from pre_workbench.guihelper import navigateLink, setControlColors


def ExpandSysPara(s):
	#TODO
	return s

class DefaultsDict(dict):
	def __init__(self):
		super().__init__()

	def getWithDefault(self, attr , attrName: str):
		#print(attrName+"?",attr)
		if isinstance(attr, dict):
			attr = attr.get(attrName)

		if (attr is None):
			if (attrName in self):
				attr = self[attrName];
			else:
				raise Exception("Erforderliches Attribut " + attrName + " fehlt.");

		else:
			attr = re.sub(r"@([A-Z0-9_]+)",
						  lambda match: self[match.group(1)] if match.group(1) in self else str(match),
						  ExpandSysPara(attr),)
			if (attr.endswith("%")):
				try:
					deff = float(self[attrName])
					at = float(attr[:-1])
					attr = str(math.round(deff * at / 100))
				except ValueError:
					pass

			if (attr.startswith("+") or attr.startswith("-")):
				if (attr.startswith("+")): attr = attr[1:]
				try:
					deff = int(self[attrName])
					at = int(attr)
					attr = str(deff + at)
				except ValueError:
					pass
		#print(attrName+"=",attr)
		return attr



class FormularParser2(QFrame):
	SubmitForm = pyqtSignal()
	TabChanged = pyqtSignal()
	EditConfirmed = pyqtSignal(str, object)

	def __init__(self):
		super(FormularParser2, self).__init__()
		self.formTag = "form"
		self.formFilespec = ""
		self.formId = ""

		self.contentPanels = list() #new List<Panel>();

		self.defaultsSection = DefaultsDict()
		self.defaultsInput = DefaultsDict()

		self.values = dict() #new Dictionary<string, string>();
		self.oldValues = dict() #new Dictionary<string, string>();
		self.Editable = False #: get; set; #}
		self.Dirty = False #: get; set; #}
		#//public List<String> tabs = new List<String>();

		self.sqlQuery = ""
		self.queryParams = dict() #new Dictionary<string,string>();
		self._parser = None

		#public event EventHandler SubmitForm;
		#public event EventHandler TabChanged;
		#public delegate void EditConfirmedEventHandler(object sender, EditConfirmedEventArgs e);
		#public event EditConfirmedEventHandler EditConfirmed;
		#public class EditConfirmedEventArgs : EventArgs:
		#	public String ID; public bool Cancel = false; public FormularInputLabel InputLabel;
		#	public EditConfirmedEventArgs(String id, FormularInputLabel control): ID = id; InputLabel = control; #}
		##}

		#ContextMenuStrip icmMenu = new ContextMenuStrip();
		#FormularInputLabel icmCurrentElement;

		#int index = 1;

		#public FormularParser2(Panel theRootPanel):
		self.clear()
		fnt = self.font()
		#fnt.setFamily("Helvetica")
		fnt.setFamilies(["Arial","sans-serif"])
		fnt.setPointSizeF(12)
		self.setFont(fnt)
		#self.setFont(QFont("sans-serif", 8.25))
		print(self.font().toString())
		self.setStyleSheet("""
		QLineEdit { border: 0; padding: 1px 1px 1px 6px;  } 
		QLineEdit:hover { border: 1px solid black; padding-left: 5px } 
		""")
		##}


	def clear(self):
		while True:
			el = self.findChild(QWidget, options=QtCore.Qt.FindDirectChildrenOnly)
			if el == None: break
			el.setParent(None)
			el.deleteLater()

		self.Dirty = False;
		self.formFilespec = "";
		self.contentPanels.clear();

		self.queryParams.clear();

		self.defaultsSection["top"] = "0";
		self.defaultsSection["left"] = "10";
		self.defaultsSection["width"] = "1000";
		self.defaultsSection["height"] = "400";
		self.defaultsSection["visible"] = "yes";
		self.defaultsSection["bgcolor"] = "#FFFFFF";
		self.defaultsSection["tabname"] = "";
		self.defaultsInput["disabled"] = "";
		self.defaultsInput["font"] = "";
		self.defaultsInput["labelfont"] = "";
		self.defaultsInput["textfont"] = "";
		self.defaultsInput["break"] = "yes";
		self.defaultsInput["bgcolor"] = "#dedbc6";
		self.defaultsInput["color"] = "#000000";
		self.defaultsInput["qtstyle"] = "";
		self.defaultsInput["labelbgcolor"] = "#808080";
		self.defaultsInput["labelcolor"] = "#c0c0c0";
		self.defaultsInput["labelqtstyle"] = "";
		self.defaultsInput["textbgcolor"] = "#88ffffff";
		self.defaultsInput["textcolor"] = "#000000";
		self.defaultsInput["textqtstyle"] = "";
		self.defaultsInput["marginleft"] = "0";
		self.defaultsInput["script"] = "";
		self.defaultsInput["scriptpara"] = "";
		self.defaultsInput["value"] = "";
		self.defaultsInput["labelpos"] = "w"; #//west
		self.defaultsInput["db"] = "inherit"; #//database flags

		self.rowLefts = None
		self.rowWidths = None
		self.index = 0

	def parseString(self, xml):
		try:
			self._prepareParser()
			self._parser.Parse(xml, True)
		except xml.parsers.expat.ExpatError as xmlex:
			msg = str(xmlex)
			self.createErrMes("Fehler beim Einlesen des Skript-Formulars<br>" + msg);
			#//MessageBox.Show(msg, "Fehler beim Einlesen der Formularinformationen", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
		except Exception as ex:
			self.createErrMes("Fehler beim Einlesen des Skript-Formulars<br>" + str(ex));


	def parseFile(self, filespec):
		formFilespec = filespec;
		try:
			self._prepareParser()
			with open(filespec, "rb") as file:
				self._parser.ParseFile(file)
		except xml.parsers.expat.ExpatError as xmlex:
			msg = "Dateiname: <a href='NAVIGATE::" + filespec + "::" + str(xmlex.lineno) + "::" + str(xmlex.offset) + "'>" + filespec + "</a><br>" + str(xmlex)+"<br>"
			self.createErrMes("Fehler beim Einlesen des Skript-Formulars<br>" + msg);
			#//MessageBox.Show(msg, "Fehler beim Einlesen der Formularinformationen", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
		except Exception as ex:
			self.createErrMes("Fehler beim Einlesen des Skript-Formulars<br>" + str(ex));


	def _prepareParser(self):
		self._parser = xml.parsers.expat.ParserCreate()
		self._parser.StartElementHandler = self._xml_start_el
		self._parser.EndElementHandler = self._xml_end_el
		self._parser.CharacterDataHandler = self._xml_cdata
		self.controlStack = list() #new Stack<Control>();
		self._xml_content_dest = None

	def _xml_cdata(self, data):
		if isinstance(self._xml_content_dest, str):
			self.queryParams[self._xml_content_dest] = self.queryParams.get(self._xml_content_dest, "") + data
		if isinstance(self._xml_content_dest, QWidget):
			self._xml_content_dest.setText(data)

	def _xml_start_el(self, name, attrs):
		if name == "row":
			parent = self.controlStack[-1]
			self.createRow(attrs, parent);
		elif name == "tabs" or name == "section":
			if len(self.controlStack) == 0: return
			tabname = self.defaultsSection.getWithDefault(attrs, "tabname");
			self.controlStack.append(self.createSection(name, attrs, tabname, self.controlStack[-1]));

		elif name == "cursor" or name == "defaults":
			if len(self.controlStack) == 0: return
			for k,v in attrs.items():
				#	//ScriptConsole.debug("Attribute: " + k + " | " + v);
				self.defaultsInput[k] = self.defaultsInput.getWithDefault(v, k);


		elif name == "input":
			if len(self.controlStack) == 0: return;
			parent = self.controlStack[-1]
			if (parent is None): raise Exception("Parent of input element must be section");
			self.createInput(attrs, parent);

		elif name == "p": #//description paragraph
			if len(self.controlStack) == 0: return
			parent = self.controlStack[-1]
			if (parent is None): raise Exception("Parent of paragraph element must be section");
			self.createDescription(attrs, parent);

		elif name == "query":
			if len(self.controlStack) == 0: return
			self._xml_content_dest = "QUERY"

		elif name == "param":
			if len(self.controlStack) == 0: return
			self._xml_content_dest = attrs["name"]

		elif name == "col":
			if len(self.controlStack) == 0: return
			key = attrs["key"].lower();
			if ("width" in attrs):
				self.queryParams["col_width_" + key] = attrs["width"];
			if ("db" in attrs):
				self.queryParams["col_dbflags_" + key] = attrs["db"];

		else:
			if (name == self.formTag):
				self.controlStack.append(self);
				self.formId = attrs["id"]



	def _xml_end_el(self, name):
		self._xml_content_dest = None
		if name == "row":
			self.rowLefts = self.rowWidths = None

		elif name == "tabs" or name == "section":
			if (len(self.controlStack) == 0): return
			self.controlStack.pop();

		else:
			if (name == self.formTag):
				self.controlStack.pop();


	def createErrMes(self, msg):
		t = QTextBrowser(self)
		t.move(0, 0); t.resize(500,300)
		traceback.print_exc()
		t.setHtml(msg + "<hr><pre>"+traceback.format_exc()+"</pre>")
		t.anchorClicked.connect(lambda url: navigateLink(url))
		#t.setStyleSheet("background-color: yellow")
		setControlColors(t, "#ffeeaa", "#ff0000")
		t.show()



	def CalculateSize(self):
		height = 0; width = 0;
		for ctrl in self.contentPanels:
			pos = ctrl.pos(); size = ctrl.size()
			if (pos.y() + size.height() > height): height = pos.y() + size.height()
			if (pos.x() + size.width() > width): width = pos.x() + size.width()

		return (width, height)


	def createSection(self, name, attrs, tabname, parent):
		if (name == "tabs"):
			p = QTabWidget(parent)
		elif isinstance(parent, QTabWidget):
			p = QFrame()
			parent.addTab(p, tabname)
			self.contentPanels.append(p)
			p.setAutoFillBackground(True)
		else:
			p = QFrame(parent)
			self.contentPanels.append(p)
			p.setVisible(self.defaultsSection.getWithDefault(attrs, "visible") == "yes")
			p.setAutoFillBackground(True)

		p.move(int(self.defaultsSection.getWithDefault(attrs, "left")),
			int(self.defaultsSection.getWithDefault(attrs, "top")))
		p.resize(int(self.defaultsSection.getWithDefault(attrs, "width")),
				 int(self.defaultsSection.getWithDefault(attrs, "height")))
		p.Tag = tabname

		setControlColors(p, bg=self.defaultsSection.getWithDefault(attrs, "bgcolor"))
		return p




	def createRow(self, attrs, parentControl):
		labelPos = self.defaultsInput.getWithDefault(attrs, "labelpos")[0];
		labelWidth = int(self.defaultsInput.getWithDefault(attrs, "labelsize"));
		if (not "label" in attrs): labelWidth = 0;

		editWidth = int(self.defaultsInput.getWithDefault(attrs, "size")) - labelWidth;

		xPos = int(self.defaultsInput.getWithDefault(attrs, "left"));
		yPos = int(self.defaultsInput.getWithDefault(attrs, "top"));

		l = None
		if (labelWidth > 0):
			l = QLabel(parentControl)
			#l.AutoSize = false; l.Height = 18;
			if labelPos == 'n':
				l.move(xPos, yPos); width = editWidth; yPos += 18; l.setAlignment(QtCore.Qt.AlignLeft)
			elif labelPos == 's':
				l.move(xPos, yPos + 17); width = editWidth
			elif labelPos == 'e':
				l.move(xPos + editWidth, yPos); width = labelWidth
			elif labelPos == 'w':
				l.move(xPos, yPos); width = labelWidth; xPos += labelWidth; l.setAlignment(QtCore.Qt.AlignRight)

			l.resize(width, 18)
			l.setText(attrs["label"])
			l.setFont(self.parseFont(self.defaultsInput.getWithDefault(attrs, "labelfont")))
			#TODO l.BackColor = ColorTranslator.FromHtml(self.defaultsInput.getWithDefault(attrs, "labelbgcolor"));
			#TODO l.ForeColor = ColorTranslator.FromHtml(self.defaultsInput.getWithDefault(attrs, "labelcolor"));
			setControlColors(l, self.defaultsInput.getWithDefault(attrs, "labelbgcolor"),
							 self.defaultsInput.getWithDefault(attrs, "labelcolor"))
			l.setStyleSheet(self.defaultsInput.getWithDefault(attrs, "labelqtstyle"));

		#}

		ratio = [float(r) for r in attrs["ratio"].split(',')]
		ratioSum = sum(ratio)
		self.rowLefts = [xPos for r in ratio]
		self.rowWidths = [math.floor(r * editWidth / ratioSum) for r in ratio]
	#}

	def createInput(self, attrs, parentControl):
		print("")
		labelPos = self.defaultsInput.getWithDefault(attrs, "labelpos")[0]
		labelWidth = int(self.defaultsInput.getWithDefault(attrs, "labelsize"))
		if (not "label" in attrs): labelWidth = 0
		width = int(self.defaultsInput.getWithDefault(attrs, "size"))
		marginLeft = int(self.defaultsInput.getWithDefault(attrs, "marginleft"))
		editWidth = int(self.defaultsInput.getWithDefault(attrs, "size")) - labelWidth
		if "size" not in attrs: editWidth -= marginLeft
		xPos = int(self.defaultsInput.getWithDefault(attrs, "left")) + marginLeft
		yPos = int(self.defaultsInput.getWithDefault(attrs, "top"))

		l = None
		if (labelWidth > 0):
			l = QLabel(parentControl)
			#l.AutoSize = false; l.Height = 18;
			if labelPos == 'n':
				l.move(xPos, yPos); labelWidth = editWidth; yPos += 18; l.setAlignment(QtCore.Qt.AlignLeft)
			elif labelPos == 's':
				l.move(xPos, yPos + 17); labelWidth = editWidth
			elif labelPos == 'e':
				l.move(xPos + editWidth, yPos); labelWidth = labelWidth
			elif labelPos == 'w':
				l.move(xPos, yPos); labelWidth = labelWidth; xPos += labelWidth; l.setAlignment(QtCore.Qt.AlignRight)

			l.resize(labelWidth, 18)
			l.setText(attrs["label"])
			l.setFont(self.parseFont(self.defaultsInput.getWithDefault(attrs, "labelfont")))
			#TODO l.BackColor = ColorTranslator.FromHtml(self.defaultsInput.getWithDefault(attrs, "labelbgcolor"));
			#TODO l.ForeColor = ColorTranslator.FromHtml(self.defaultsInput.getWithDefault(attrs, "labelcolor"));
			l.setStyleSheet("background-color: " + self.defaultsInput.getWithDefault(attrs, "labelbgcolor")
							+ ";color: " + self.defaultsInput.getWithDefault(attrs, "labelcolor")
							+ ";" + self.defaultsInput.getWithDefault(attrs, "labelqtstyle"));


		id = attrs["id"]
		print(">>>", id, xPos, yPos, marginLeft, width)
		lPadding = QLineEdit(parentControl);
		lPadding.move(xPos, yPos);
		lPadding.resize(editWidth, 17);
		lPadding.setObjectName(id);
		lPadding.setDisabled(self.defaultsInput.getWithDefault(attrs, "disabled") == "yes");
		lPadding.setFont(self.parseFont(self.defaultsInput.getWithDefault(attrs, "font")));
		style = ("background-color: " + self.defaultsInput.getWithDefault(attrs, "bgcolor")
			+ ";color: " + self.defaultsInput.getWithDefault(attrs, "color")
			+ ";" + self.defaultsInput.getWithDefault(attrs, "qtstyle"))
		print(style)
		lPadding.setStyleSheet(style);
		lPadding.setProperty("declarationLine", self._parser.CurrentLineNumber);
		lPadding.show();
		for k,v in attrs.items():
			lPadding.setProperty(k,v)

		if self.defaultsInput.getWithDefault(attrs, "value") != "" or "value" in attrs:
			self.values[id] = self.defaultsInput.getWithDefault(attrs, "value");
			self.updateValues(id)
		#}

		lPadding.ScriptPara = self.defaultsInput.getWithDefault(attrs, "scriptpara");
		scriptName = self.defaultsInput.getWithDefault(attrs, "script");
		#if (scriptName != ""):
		#	ScriptContext.Script cls = App.Script.getScriptClass(scriptName);
		#	IFormularInputHandler script = (IFormularInputHandler)cls;
		#	lPadding.HandlerScript = script;
		#	lPadding.ScriptName = scriptName;
		#
		#	script.OnCreate(lPadding);
		#}
		if (id in self.values): lPadding.setText(self.values[id]);
		lineBreak = self.defaultsInput.getWithDefault(attrs, "break");
		if (lineBreak == "auto"): lineBreak = "no" if (marginLeft + width + 2 < int(self.defaultsInput["size"])) else "yes";
		if (lineBreak != "no"):
			self.defaultsInput["top"] = str(max(lPadding.pos().y() + lPadding.height() + 1, 0 if (l is None) else l.pos().y()+l.height()));
			self.defaultsInput["marginleft"] = "0";
		else:
			self.defaultsInput["marginleft"] = str(marginLeft + width + 2)
			print(marginLeft, width)
		#}
		if (self.defaultsInput.getWithDefault(attrs, "db") != "inherit"):
			self.queryParams["col_dbflags_" + id.lower()] = self.defaultsInput.getWithDefault(attrs, "db");
		self.index += 1
	#}


	def setSectionOption(self, key,  value):
		self.defaultsSection[key] = self.defaultsSection.getWithDefault(value, key)
	#}
	def setInputOption(self, key,  value):
		self.defaultsInput[key] = self.defaultsInput.getWithDefault(value, key)
	#}

	def createDescription(self, attrs, parentControl):
		width = int(self.defaultsInput.getWithDefault(attrs, "size"))
		marginLeft = int(self.defaultsInput.getWithDefault(attrs, "marginleft"))
		editWidth = width
		if "size" in attrs: editWidth -= marginLeft
		xPos = int(self.defaultsInput.getWithDefault(attrs, "left")) + marginLeft
		yPos = int(self.defaultsInput.getWithDefault(attrs, "top"))
		breakValue = self.defaultsInput.getWithDefault(attrs, "break")

		lPadding = QLabel(parentControl)
		lPadding.move(xPos, yPos)

		try:
			height = int(attrs["height"])
		except:
			height = 17
		lPadding.resize( editWidth, height)

		lPadding.setContentsMargins(10, 1, 1, 1);
		lPadding.setFont(self.parseFont(self.defaultsInput.getWithDefault(attrs, "textfont")))
		lPadding.setStyleSheet("background-color: " + self.defaultsInput.getWithDefault(attrs, "textbgcolor")
						+ ";color: " + self.defaultsInput.getWithDefault(attrs, "textcolor")
						+ ";" + self.defaultsInput.getWithDefault(attrs, "textqtstyle"));
		self._xml_content_dest = lPadding


		if (breakValue != "no"):
			self.defaultsInput["top"] = str(lPadding.pos().y() + height + 1);
			self.defaultsInput["marginleft"] = "0";
		else:
			self.defaultsInput["marginleft"] = str(marginLeft + width + 2);

		self.index += 1


	def parseFont(self, info):
		font = QFont(self.font())
		for s in info.split(' '):
			s = s.strip().lower()
			if (s.endswith("pt")):
				font.setPointSizeF(float(s[:-2]))

			elif s == "bold" or s == "b": font.setBold(True)
			elif s == "italic" or s == "i": font.setItalic(True)
			elif s == "underline" or s == "u": font.setUnderline(True)
			elif s == "strike": font.setStrikeOut(True)
		print(font.toString())
		return font

	def updateValues(self, id):
		for fil in self.findChildren(QLineEdit, name=id):
			fil.setText(self.values[id]);

	def findById(self, id):
		return self.findChild(QLineEdit, name=id)



	def loadFromDataReader(self, cursor):
		self.loadFromDict()
	def loadFromDict(self, d):
		for tx in self.findChildren(QLineEdit):
			FormularInputLabel tx = ctrl as FormularInputLabel;
			if (tx != null && tx.ID != null && !isDbFlagSet(tx.ID, "ignore")):
				try:
					string loadFromField = tx.ID;
					object dataValue = reader[loadFromField];
					string value = dataValue.ToString();
					if (dataValue is DateTime) value = ((DateTime)dataValue).ToString("yyyy-MM-dd");
					this.values[loadFromField] = value;
					if (dataValue == DBNull.Value) this.oldValues[loadFromField] = null;
					else this.oldValues[loadFromField] = value;
					tx.UpdateText(value);
				catch (Exception ex):
					if (tx.ID.StartsWith("__") or isDbFlagSet(tx.ID, "optional")) continue;
					tx.Tag = null; tx.Text = "ERR: " + ex.Message; tx.ForeColor = Color.Red;

		self.Dirty = False

"""
	def getQueryParam(string paramName):
		string p;
		if(!queryParams.TryGetValue(paramName.lower(), out p)) return "";
		return p;
	#}
	def isDbFlagSet(string colName, string flag):
		return (" "+(getQueryParam("col_dbflags_" + colName).lower())+" ").Contains(" "+flag+" ");
	#}

	def saveToDb(string table, string whereClause, ref long ID, out int okCount):
		bool isNew = (ID == 0);
		if (queryParams.ContainsKey("scriptbeforesave")):
			ScriptContext.Script cls = App.Script.getScriptClass(queryParams["scriptbeforesave"]);
			if ((bool)cls.Execute(this,  isNew ? "NEW" : ID.ToString()) == false):
			//if ((bool)cls.RunScript(new Dictionary<string, object>():: "formular" , this#},: "id",isNew ? "NEW" : ID.ToString()#}#}) == false):
				okCount = 0;
				return false;
			#}
		#}

		if (isNew):
			//int ok = App.DB.ExecuteSQL("INSERT INTO " + table + " () VALUES ()");
			var dict = new Dictionary<string, object>();
			foreach (KeyValuePair<string, string> newVals in this.values):
				if (newVals.Key.StartsWith("__") or isDbFlagSet(newVals.Key, "readonly") or isDbFlagSet(newVals.Key, "ignore")) continue;
				dict[newVals.Key] = newVals.Value;
			#}
			int ok = App.DB.Insert(table, dict);
			if (ok == 0):
				MessageBox.Show("Neuer Datensatz vom Typ "+table+" konnte nicht angelegt werden.","", MessageBoxButtons.OK, MessageBoxIcon.Error);
				okCount = 0;
				return false;
			#}
			ID = App.DB.lastInsertId();
			okCount = dict.Count;
			foreach (KeyValuePair<string, object> newVals in dict):
				oldValues[newVals.Key] = (string)newVals.Value;
			#}
			this.Dirty = false;
			return true;
		#}

		string errors = "";
		okCount = 0;
		foreach (KeyValuePair<string, string> newVals in this.values):
			if (newVals.Key.StartsWith("__") or isDbFlagSet(newVals.Key, "readonly") or isDbFlagSet(newVals.Key, "ignore")) continue;
			string oldValue;
			if (this.oldValues.TryGetValue(newVals.Key, out oldValue) && newVals.Value == oldValue) continue;
			ScriptConsole.debug("Updating column " + newVals.Key + " from value \"" + oldValue + "\" to \"" + newVals.Value + "\"");
			try:
				int ok;
				if (oldValue is None)
					ok = App.DB.ExecuteSQL("UPDATE " + table + " SET `" + newVals.Key + "` = ? WHERE " + whereClause + " AND (`" + newVals.Key + "` IS NULL  )",
						newVals.Value, ID);
				else
					ok = App.DB.ExecuteSQL("UPDATE " + table + " SET `" + newVals.Key + "` = ? WHERE " + whereClause + " AND (`" + newVals.Key + "` = ?  )",
						newVals.Value, ID, oldValue);
				if (ok == 0) errors += newVals.Key + "; ";
				else:
					okCount++;
					oldValues[newVals.Key] = newVals.Value;
				#}
			catch (Exception ex):
				ScriptConsole.exception(Severity.Warning, "saveToDbErr", ex);
				ScriptConsole.warn("Failed to save column " + newVals.Key);
				errors += "\n"+newVals.Key;
			#}
		#}
		if (errors != ""):
			MessageBox.Show("Folgende Einträge konnten nicht gespeichert werden: " + errors, "", MessageBoxButtons.OK, MessageBoxIcon.Error);
			return false;
		else:
			this.Dirty = false;
			return true;
		#}
	#}
	"""

	def loadEmptyData(self):
		for tx in self.findChildren(QLineEdit):
			id = tx.property("id")
			if id is not None:
				self.values[tx.objectName()] = "";
				self.oldValues[tx.objectName()] = "";
				tx.setText("");

	def set(self, key, value):
		if (value is None): value = "";
		self.values[key] = value;
		self.updateValues(key);
		self.Dirty = True;
	#}
	def get(self, key, defaultValue=None):
		return self.values.get(key, defaultValue)

	def position(self, left,  top):
		self.defaultsInput["left"] = self.defaultsInput.getWithDefault(left, "left");
		self.defaultsInput["top"] = self.defaultsInput.getWithDefault(top, "top");
	#}
	def isModified(self, key):
		if ( key not in self.values): return False;
		if (key not in self.oldValues): return True
		return (self.values[key] != self.oldValues[key]);
	#}


#}


def run_app():
	from PyQt5.QtWidgets import QApplication

	import sys
	app = QApplication(sys.argv)
	ex = FormularParser2()
	ex.parseFile("/Users/mw/Downloads/ares_OLD/AdressDetails.v3.xml")
	ex.show()
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())


if __name__ == '__main__':
	run_app()

