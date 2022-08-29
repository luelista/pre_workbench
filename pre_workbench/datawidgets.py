# PRE Workbench
# Copyright (C) 2022 Mira Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import html
import itertools
import logging
from base64 import b64encode, b64decode
from typing import Optional, List, Tuple

import yaml
from PyQt5.QtCore import (Qt, pyqtSignal, QAbstractItemModel, QModelIndex, pyqtSlot)
from PyQt5.QtWidgets import QTextEdit, QTabWidget, QWidget, QVBoxLayout, \
    QMenu, \
    QAbstractItemView, QTableView, QAction, QInputDialog, QMessageBox

import pre_workbench.app

from pre_workbench.configs import SettingsField, getIcon
from pre_workbench.guihelper import getMonospaceFont, setClipboardText, getClipboardText, APP
from pre_workbench.structinfo.expr import Expression
from pre_workbench.controls.genericwidgets import showSettingsDlg, showListSelectDialog
from pre_workbench.typeeditor import JsonView
from pre_workbench.controls.hexview import HexView2
from pre_workbench.objects import ByteBuffer, ByteBufferList
from pre_workbench.typeregistry import DataWidgetTypes


class ColumnInfo:
    def __init__(self, expr_str, title=None):
        self.expr = Expression(expr_str=expr_str)
        if title == None: title = expr_str
        self.title = title

    def extract(self, bbuf : ByteBuffer):
        return self.expr.evaluate_bbuf(bbuf)

    def __str__(self):
        return self.title
    def __repr__(self):
        return "ColumnInfo(%s, %s)" % (self.title, self.expr.expr_str)
    def toDict(self):
        return {"title":self.title, "expr_str":self.expr.expr_str}

def get_wireshark_colset():
    return [ColumnInfo("frame.time", src="meta"), ColumnInfo("frame.len", src="meta"),
            ColumnInfo("frame.number", src="meta"), ColumnInfo("frame.protocols", src="meta"),
            ColumnInfo("eth.src"), ColumnInfo("eth.dst"), ColumnInfo("eth.type"),
            ColumnInfo("ip.src"), ColumnInfo("ip.dst"), ColumnInfo("ip.proto"),
            ColumnInfo("Payload", key="tcp.payload", show="hex")]

class PacketListModel(QAbstractItemModel):
    columns: List[ColumnInfo]
    listObject: Optional[ByteBufferList]

    def __init__(self, plist: Optional[ByteBufferList] = None, parent = None):
        super().__init__(parent)
        self.columns = []
        self.listObject = None
        self.setList(plist)
        #self.rootItem = TreeItem(("Model", "Status","Location"))

    def setList(self, plist: Optional[ByteBufferList]):
        if self.listObject is not None:
            self.listObject.on_new_packet.disconnect(self.onNewPacket)
        self.beginResetModel()
        self.listObject = plist
        self.endResetModel()
        if len(self.columns) == 0:
            self.autoCols()
        if self.listObject is not None:
            self.listObject.on_new_packet.connect(self.onNewPacket)

    def autoCols(self):
        self.beginResetModel()
        if self.rowCount(None) > 0:
            self.columns = list(itertools.islice(itertools.chain(
                (ColumnInfo("hex(payload)", "payload"),),
                (ColumnInfo("${\"" + x + "\"}", "$" + x) for x in self.listObject.buffers[0].metadata.keys()),
                (ColumnInfo("fields[\"" + x + "\"]", x) for x in self.listObject.buffers[0].fields.keys())
            ), 12))
        self.endResetModel()

    def onNewPacket(self, count):
        if count < 1: return
        idx = len(self.listObject)
        logging.debug("onNewPacket %d/%d",idx,count)
        self.beginInsertRows(QModelIndex(), idx - count, idx - 1)
        self.endInsertRows()
        if len(self.columns) == 0:
            self.autoCols()

    def columnCount(self, parent):
        return len(self.columns)

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole:
            return None

        if self.listObject is None:
            return None

        item = self.listObject.buffers[index.row()]
        col_info = self.columns[index.column()]
        try:
            return str(col_info.extract(item))
        except Exception as ex:
            logging.warning("Data error: %s", ex)
            return "ERROR: "+str(ex)

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= len(self.columns):
                return None
            return self.columns[section].title

        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            if self.listObject is None:
                return None
            item = self.listObject.buffers[section]
            return "X" if item.metadata.get("marked", False) else " "

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        return self.createIndex(row, column)

    def rowCount(self, parent):
        if self.listObject is None: return 0
        return len(self.listObject)

    def addColumn(self, colInfo: ColumnInfo, insertBefore: Optional[int] = None):
        if insertBefore == None: insertBefore = len(self.columns)
        self.beginInsertColumns(QModelIndex(), insertBefore, insertBefore)
        self.columns.insert(insertBefore, colInfo)
        self.endInsertColumns()

    def removeColumns(self, column: int, count: int, parent: QModelIndex = ...) -> bool:
        self.beginRemoveColumns(parent, column, column+count-1)
        self.columns = self.columns[0:column] + self.columns[column+count:]
        self.endRemoveColumns()
        return True

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def markPacket(self, rowIndex):
        data = self.listObject.buffers[rowIndex]
        data.metadata['marked'] = not data.metadata.get('marked', False)
        self.headerDataChanged.emit(Qt.Vertical, rowIndex, rowIndex)



@DataWidgetTypes.register(handles=ByteBufferList)
class PacketListWidget(QWidget):
    meta_updated = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self.lastFindExpression = ""
        self.initUI()

    def showData(self, data: List[ByteBuffer]):
        dv = DynamicDataWidget()
        dv.setContents(data)
        dv.setWindowTitle("Item Details")
        pre_workbench.app.MainWindow.showChild(dv, True)

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.NoFocus)
        #tabs = QTabWidget()
        #layout.addWidget(tabs)

        self.packetlist = QTableView()
        self.packetlist.setFont(getMonospaceFont())
        self.packetlist.setSortingEnabled(True)
        self.packetlist.setContextMenuPolicy(Qt.CustomContextMenu)
        self.packetlist.customContextMenuRequested.connect(self.onPacketlistContextMenu)
        self.packetlist.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.packetlist.horizontalHeader().customContextMenuRequested.connect(self.onHeaderContextMenu)
        self.packetlist.horizontalHeader().setSectionsClickable(False)
        self.packetlist.horizontalHeader().setSectionsMovable(True)
        self.packetlist.verticalHeader().setMinimumWidth(20)
        self.packetlist.verticalHeader().sectionClicked.connect(self._rowHeaderClicked)
        self.packetlist.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.packetlistmodel = PacketListModel()
        #self.packetlistmodel.rowsInserted.connect(lambda a,b,c: tabs.setTabText(0, "Raw Frames (%d)"%self.packetlistmodel.rowCount(QModelIndex())))
        self.packetlist.setModel(self.packetlistmodel)
        self.packetlist.selectionModel().selectionChanged.connect(self.onPacketlistSelectionChanged)
        self.packetlist.selectionModel().currentChanged.connect(self.onPacketlistCurrentChanged)
        #tabs.addTab(self.packetlist, "Raw Frames")
        layout.addWidget(self.packetlist)
        self.ctx_item_actions = [
            QAction(getIcon("document-search-result.png"), "Item Details", triggered=lambda: self.showData(self.getSelectedBuffers()), enabled=False),
            QAction(getIcon("flag.png"), "Mark/Unmark Selected Packets", triggered=self._markUnmarkSelection, enabled=False),
        ]
        self.ctx_general_actions = [
            QAction(getIcon("binocular-flag.png"), "Find By Expression", triggered=self._findByExpression),
        ]
        self.actions = self.ctx_item_actions + self.ctx_general_actions + [
            QAction(getIcon("table-reset.png"), "Reset Header", triggered=lambda: self.packetlistmodel.autoCols()),
            QAction(getIcon("table-insert-column-tag.png"), "Add Metadata Column", triggered=lambda: self._quickAddDialog("Quick Add Metadata Column", self._getQuickAddMetadataElements(), None)),
            QAction(getIcon("table-insert-column-bookmark.png"), "Add Field Column", triggered=lambda: self._quickAddDialog("Quick Add Field Column", self._getQuickAddFieldElements(), None)),
        ]

    def _findByExpression(self):
        expr_str = QInputDialog.getText(self, "Find By Expression", "Please enter expression. All rows for which the expression is true will be marked, all others unmarked.", text=self.lastFindExpression)[0]
        if not expr_str: return
        self.lastFindExpression = expr_str
        expr = Expression(expr_str=expr_str)
        matches = 0
        for rowIndex, buf in enumerate(self.packetlistmodel.listObject.buffers):
            match = buf.metadata['marked'] = bool(expr.evaluate_bbuf(buf))
            if match: matches += 1
            self.packetlistmodel.headerDataChanged.emit(Qt.Vertical, rowIndex, rowIndex)
        QMessageBox.information(self, "Find By Expression", f"Of {len(self.packetlistmodel.listObject.buffers)} buffers, {matches} matched the expression " + expr.serialize())

    def _rowHeaderClicked(self, rowIndex: int):
        self.packetlistmodel.markPacket(rowIndex)

    def setContents(self, lstObj: Optional[ByteBufferList]):
        self.listObject = lstObj
        #logging.debug("PacketListWidget::setContents %r %d", lstObj, len(lstObj))
        self.setWindowTitle(str(lstObj))
        self.packetlistmodel.setList(self.listObject)
        self.meta_updated.emit("actions", self.actions)

    def onPacketlistSelectionChanged(self, selected, deselected):
        buffers = list()
        for index in self.packetlist.selectionModel().selectedRows():
            buffers.append(self.listObject.buffers[index.row()])
        self.meta_updated.emit("zoom", buffers)
        for action in self.ctx_item_actions:
            action.setEnabled(len(buffers) > 0)

    def onPacketlistCurrentChanged(self, current, previous):
        pass

    def getSelectedBuffers(self):
        return [self.listObject.buffers[index.row()] for index in self.packetlist.selectionModel().selectedRows()]

    def onPacketlistContextMenu(self, point):
        index = self.packetlist.indexAt(point)
        ctx = QMenu("Context menu", self.packetlist)
        if index.isValid():
            for action in self.ctx_item_actions:
                ctx.addAction(action)
            self._buildRunMacroOnBufferSubmenu(ctx, "Run Macro On" + (" Selected Buffers" if len(self.packetlist.selectionModel().selectedRows()) > 1 else " Buffer"))
            ctx.addSeparator()
        ctx.addAction("Select All", lambda: self.packetlist.selectAll())
        for action in self.ctx_general_actions:
            ctx.addAction(action)

        ctx.exec(self.packetlist.viewport().mapToGlobal(point))

    def _markUnmarkSelection(self):
        [self.packetlistmodel.markPacket(index.row()) for index in self.packetlist.selectionModel().selectedRows()]

    def _buildRunMacroOnBufferSubmenu(self, ctx, title):
        menu = ctx.addMenu(title)
        for container_id, container, macroName in APP().find_macros_by_input_types(["BYTE_BUFFER", "BYTE_BUFFER_LIST"]):
            menu.addAction(macroName, lambda c=container, name=macroName: self._runMacroOnSelectedBuffers(c, name))

    def _runMacroOnSelectedBuffers(self, container, macroname):
        macro = container.getMacro(macroname)
        if macro.input_type == "BYTE_BUFFER":
            for buf in self.getSelectedBuffers():
                macro.execute(buf)
        elif macro.input_type == "BYTE_BUFFER_LIST":
            lst = ByteBufferList()
            for index in self.packetlist.selectionModel().selectedRows():
                lst.add(self.listObject.buffers[index.row()])
            macro.execute(lst)

    def _quickAddDialog(self, title: str, elements: List[Tuple[str, str]], addIdx: int):
        def on_ok(keys):
            for key in keys:
                self.packetlistmodel.addColumn(ColumnInfo(key, key), addIdx)
        showListSelectDialog(elements, None, title, self, on_ok, multiselect=True)

    def _generateQuickAddMenu(self, ctx: QMenu, title: str, elements: List[Tuple[str, str]], addIdx: int):
        if len(elements) > 20:
            ctx.addAction(title + " ...", lambda: self._quickAddDialog(title, elements, addIdx))
        else:
            quick = ctx.addMenu(title)
            for key, text in elements:
                quick.addAction(text, lambda key=key, text=text: self.packetlistmodel.addColumn(ColumnInfo(key, text), addIdx))

    def _getQuickAddMetadataElements(self):
        return [("${\"" + key + "\"}", "$" + key) for key in
                    sorted(self.listObject.getAllKeys(metadataKeys=True, fieldKeys=False))]

    def _getQuickAddFieldElements(self):
        return [("fields[\""+key+"\"]", key) for key in
                    sorted(self.listObject.getAllKeys(metadataKeys=False, fieldKeys=True))]

    def onHeaderContextMenu(self, point):
        index = self.packetlist.horizontalHeader().logicalIndexAt(point)

        ctx = QMenu("Context menu", self.packetlist)
        if index > -1:
            ctx.addAction("Header "+str(index)).setDisabled(True)
            ctx.addAction("Edit", lambda: self.onEditColumn(index))
            ctx.addAction("Remove Column", lambda: self.packetlistmodel.removeColumn(index))
            ctx.addSeparator()
        addIdx = None if index == -1 else index
        ctx.addAction("Add Column ...", lambda: self.onAddColumn(addIdx))

        self._generateQuickAddMenu(ctx, "Quick Add Metadata Column", self._getQuickAddMetadataElements(), addIdx)

        self._generateQuickAddMenu(ctx, "Quick Add Field Column", self._getQuickAddFieldElements(), addIdx)

        ctx.addSeparator()
        magic = "!!pre_workbench/packetListHeaderState\n"
        ctx.addAction("Copy Header State", lambda: setClipboardText(magic+yaml.dump(self.saveState(), sort_keys=False)))
        if getClipboardText().startswith(magic):
            ctx.addAction("Paste Header State", lambda: self.restoreState(yaml.safe_load(getClipboardText()[len(magic):])))
        ctx.addAction("Reset Header", lambda: self.packetlistmodel.autoCols())
        ctx.exec(self.packetlist.horizontalHeader().mapToGlobal(point))

    def getColumnInfoDefinition(self) -> List[SettingsField]:
        return [
            SettingsField("expr_str", "Expression", "text", {"autocomplete":self.listObject.getAllKeys()}),
            SettingsField("title", "Column Title", "text", {}),
            #SettingsField("src", "Data source", "select", {"options":[("meta","Packet meta data"), ("field","Packet field")]}),
            #SettingsField("show", "Display mode", "select", {"options":[ ("show","Display contents"), ("showname","Tree display contents"), ("hex","Hex value") ]}),
        ]

    def onAddColumn(self, insertBefore: Optional[int]):
        par = showSettingsDlg(self.getColumnInfoDefinition(), min_width=450)
        if par is not None:
            if par["title"] == "": par["title"] = par["expr_str"]
            self.packetlistmodel.addColumn(ColumnInfo(**par), insertBefore)

    def onEditColumn(self, index: int):
        par = showSettingsDlg(self.getColumnInfoDefinition(), self.packetlistmodel.columns[index].toDict(), min_width=450)
        if par is not None:
            if par["title"] == "": par["title"] = par["key"]
            self.packetlistmodel.removeColumn(index)
            self.packetlistmodel.addColumn(ColumnInfo(**par), index)

    def run_ndis(self):
        pass

    def saveState(self) -> dict:
        return {
            "hs": bytes(self.packetlist.horizontalHeader().saveState()),
            "cols": [c.toDict() for c in self.packetlistmodel.columns],
        }

    def restoreState(self, state: dict):
        if "cols" in state:
            self.packetlistmodel.beginResetModel()
            self.packetlistmodel.columns = [ColumnInfo(**params) for params in state["cols"]]
            self.packetlistmodel.endResetModel()
        if "hs" in state:
            self.packetlist.horizontalHeader().restoreState(state["hs"])


@DataWidgetTypes.register(handles=[ByteBuffer,list])
class ByteBufferWidget(QWidget):
    meta_updated = pyqtSignal(str, object)
    def __init__(self):
        super().__init__()

        self.initUI()


    def initUI(self):
        #toolbar = QToolBar()
        #self.splitIntoPacketsAction = toolbar.addAction("Split into packets")
        #self.splitIntoPacketsAction.triggered.connect(self.splitIntoPackets)

        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.tabWidget = QTabWidget()
        self.tabWidget.setContentsMargins(0,0,0,0)
        self.tabWidget.setDocumentMode(True)
        layout.addWidget(self.tabWidget)
        self.textbox = HexView2(project=pre_workbench.app.CurrentProject, formatInfoContainer=pre_workbench.app.CurrentProject.formatInfoContainer)
        self.textbox.selectionChanged.connect(self._onSelectionChanged)
        self.textbox.onNewSubflowCategory.connect(self._newSubflowCategory)
        self.textbox.parseResultsUpdated.connect(self._onParseResultsUpdated)
        self.tabWidget.addTab(self.textbox, "Raw buffer")
        #layout.addWidget(toolbar)

    def _onSelectionChanged(self, selRange):
        selbytes = self.textbox.buffers[selRange.buffer_idx].getBytes(selRange.start, selRange.length())
        self.meta_updated.emit("selected_bytes", selbytes)
        self.meta_updated.emit("hexview_range", self.textbox)

    def setContents(self, bufObj):
        self.bufferObject = bufObj
        self.setWindowTitle(str(bufObj))
        self.textbox.setBuffer(bufObj)
        try:
            #TODO maybe remove this whole feature (tab bar etc)?
            self.bufferObject.on_new_data.connect(self.onNewData)
        except:
            pass

    def _onParseResultsUpdated(self, fi_trees):
        #TODO this is the wrong place - it happens after the newSubflowCategory calls and clears them again immediately   self.tabWidget.clear()
        #self.tabWidget.addTab(self.textbox, "Raw buffer")
        self.meta_updated.emit("grammar", fi_trees)

    def _newSubflowCategory(self, category, parse_context):
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == category:
                break
        widget = PacketListWidget()
        widget.setContents(parse_context.subflow_categories[category])
        self.tabWidget.addTab(widget, category)
        widget.meta_updated.connect(self.meta_updated.emit)

    def onNewData(self):
        #self.textbox.showHex(bufObj.buffer)
        self.textbox.redraw()

    def splitIntoPackets(self):
        pass

    def run_ndis(self):
        pass

    def clearRanges(self):
        self.textbox.clearRanges()


class DynamicDataWidget(QWidget):
    meta_updated = pyqtSignal(str, object)

    def __init__(self, *args):
        super().__init__(*args)
        self.block_zoom = False
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.metadataWidget = JsonView()
        #self.layout().addWidget(ExpandWidget("Metadata", self.metadataWidget, True), 33)
        self.layout().addWidget(self.metadataWidget, 33)
        self.metadataWidget.setVisible(False)
        self.childWidget = None
        self.setErrMes(title="No data loaded")

    def setMetadataVisible(self, visible):
        self.metadataWidget.setVisible(visible)

    @pyqtSlot(object)
    def setContents(self, data):
        typ = type(data)
        if data is None:
            self.setErrMes(title="No data selected")
        else:
            if hasattr(data, "metadata"):
                self.metadataWidget.setContents(data.metadata)
            else:
                self.metadataWidget.setContents(None)
            widgetTyp, _ = DataWidgetTypes.find(handles=typ)
            if widgetTyp is None:
                self.setErrMes("Unknown data type "+str(typ))
            else:
                self.loadChildType(widgetTyp)
                self.childWidget.setContents(data)

    def setErrMes(self, msg="", title="Error"):
        self.loadChildType(QTextEdit)
        self.childWidget.setHtml("<h4>"+title+"</h4><pre>"+html.escape(msg)+"</pre>")

    def loadChildType(self, childType):
        if isinstance(self.childWidget, childType): return
        if self.childWidget != None:
            self.layout().removeWidget(self.childWidget)
            self.childWidget.setParent(None)
        self.childWidget = None  #neccessary, so if the next line throws, the error message will be shown
        self.childWidget = childType()
        try:
            self.childWidget.meta_updated.connect(self._forwardMetaUpdate)
        except:
            logging.debug(str(childType)+" has no meta_updated signal")
        self.layout().addWidget(self.childWidget,66)

    def _forwardMetaUpdate(self, name, value):
        if self.block_zoom and name == 'zoom': return
        self.meta_updated.emit(name, value)

    def childActionProxy(self):
        return self.childWidget

