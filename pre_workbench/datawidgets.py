
# PRE Workbench
# Copyright (C) 2019 Max Weller
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

import cgi
import itertools

from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QAbstractItemModel, QModelIndex, pyqtSlot)
from PyQt5.QtWidgets import QTextEdit, QTabWidget, QTableWidget, QWidget, QToolBar, QVBoxLayout, \
    QTableWidgetItem, QMenu, \
    QAbstractItemView, QTableView

from pre_workbench.structinfo.expr import Expression
from pre_workbench.genericwidgets import showSettingsDlg
from pre_workbench.typeeditor import JsonView
from pre_workbench.hexview import HexView2
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
        return "ColumnInfo(%s, %s, %s, %s)" % (self.title, self.key, self.src, self.show)
    def toDict(self):
        return {"title":self.title, "key":self.key, "src":self.src, "show":self.show}

def get_wireshark_colset():
    return [ColumnInfo("frame.time", src="meta"), ColumnInfo("frame.len", src="meta"),
            ColumnInfo("frame.number", src="meta"), ColumnInfo("frame.protocols", src="meta"),
            ColumnInfo("eth.src"), ColumnInfo("eth.dst"), ColumnInfo("eth.type"),
            ColumnInfo("ip.src"), ColumnInfo("ip.dst"), ColumnInfo("ip.proto"),
            ColumnInfo("Payload", key="tcp.payload", show="hex")]

class PacketListModel(QAbstractItemModel):
    def __init__(self, plist=None, parent=None):
        super().__init__(parent)
        self.columns = []
        self.listObject = None
        self.setList(plist)
        #self.rootItem = TreeItem(("Model", "Status","Location"))

    def setList(self, plist):
        self.beginResetModel()
        if self.listObject is not None:
            self.listObject.on_new_packet.disconnect(self.onNewPacket)
        self.listObject = plist
        if len(self.columns) == 0:
            self.autoCols()
        if self.listObject is not None:
            self.listObject.on_new_packet.connect(self.onNewPacket)
        self.endResetModel()

    def autoCols(self):
        if self.rowCount(None) > 0:
            self.columns = list(itertools.islice(itertools.chain(
                (ColumnInfo("${\"" + x + "\"}") for x in self.listObject.buffers[0].metadata.keys()),
                (ColumnInfo(x) for x in self.listObject.buffers[0].fields.keys())
            ), 12))

    def onNewPacket(self, count):
        if count < 1: return
        idx = len(self.listObject)
        print("onNewPacket",idx,count)
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
        return col_info.extract(item)

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section >= len(self.columns):
                return None
            return self.columns[section].title

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        return self.createIndex(row, column)

    def rowCount(self, parent):
        if self.listObject is None: return 0
        return len(self.listObject)

    def addColumn(self, colInfo, insertBefore=None):
        if insertBefore == None: insertBefore = len(self.columns)
        self.beginInsertColumns(QModelIndex(), insertBefore, insertBefore)
        self.columns.insert(insertBefore, colInfo)
        self.endInsertColumns()
    def removeColumns(self, column: int, count: int, parent: QModelIndex = ...) -> bool:
        self.beginRemoveColumns(parent, column, column+count-1)
        self.columns = self.columns[0:column] + self.columns[column+count:]
        print(column, count, self.columns)
        self.endRemoveColumns()
        return True

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

@DataWidgetTypes.register(handles=ByteBufferList)
class PacketListWidget(QWidget):
    on_data_selected = pyqtSignal(QObject)

    def __init__(self):
        super().__init__()
        self.dv = None
        self.initUI()

    def showData(self, data):
        if not self.dv:
            self.dv = DynamicDataWidget()
            self.dv.setWindowTitle("Data view")
        self.dv.setContents(data)
        self.dv.show()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        #tabs = QTabWidget()
        #layout.addWidget(tabs)

        self.packetlist = QTableView()
        self.packetlist.setSortingEnabled(True)
        self.packetlist.setContextMenuPolicy(Qt.CustomContextMenu)
        self.packetlist.customContextMenuRequested.connect(self.onPacketlistContextMenu)
        self.packetlist.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.packetlist.horizontalHeader().customContextMenuRequested.connect(self.onHeaderContextMenu)
        self.packetlist.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.packetlistmodel = PacketListModel()
        #self.packetlistmodel.rowsInserted.connect(lambda a,b,c: tabs.setTabText(0, "Raw Frames (%d)"%self.packetlistmodel.rowCount(QModelIndex())))
        self.packetlist.setModel(self.packetlistmodel)
        self.packetlist.selectionModel().selectionChanged.connect(self.onPacketlistSelectionChanged)
        self.packetlist.selectionModel().currentChanged.connect(self.onPacketlistCurrentChanged)
        #tabs.addTab(self.packetlist, "Raw Frames")
        layout.addWidget(self.packetlist)

    def setContents(self, lstObj):
        self.listObject = lstObj
        print("PacketListWidget::setContents", lstObj, len(lstObj))
        self.setWindowTitle(str(lstObj))
        #for bbuf in lstObj.buffers:
        #    self.addPacketToList(bbuf)
        self.packetlistmodel.setList(self.listObject)

    def onPacketlistSelectionChanged(self, selected, deselected):
        pass
    def onPacketlistCurrentChanged(self, current, previous):
        if current.isValid():
            bbuf = self.listObject.buffers[current.row()]
            self.on_data_selected.emit(bbuf)

    def onPacketlistContextMenu(self, point):
        index = self.packetlist.indexAt(point)
        ctx = QMenu("Context menu", self.packetlist)
        if index.isValid():
            bbuf = self.listObject.buffers[index.row()]
            ctx.addAction("Item details", lambda: self.showData(bbuf))
            ctx.addSeparator()
        ctx.addAction("Select all", lambda: self.packetlist.selectAll())

        ctx.exec(self.packetlist.viewport().mapToGlobal(point))

    def onHeaderContextMenu(self, point):
        index = self.packetlist.horizontalHeader().logicalIndexAt(point)
        print(index)

        ctx = QMenu("Context menu", self.packetlist)
        if index > -1:
            ctx.addAction("Header "+str(index))
            ctx.addAction("Edit", lambda: self.onEditColumn(index))
            ctx.addAction("Remove column", lambda: self.packetlistmodel.removeColumn(index))
            ctx.addSeparator()
        addIdx = None if index == -1 else index
        ctx.addAction("Add column ...", lambda: self.onAddColumn(addIdx))
        for key in self.listObject.getAllKeys(metadataKeys=True, fieldKeys=False):
            ctx.addAction(key, lambda key=key: self.packetlistmodel.addColumn(ColumnInfo(key, src="meta"), addIdx))
        ctx.addSeparator()
        for key in self.listObject.getAllKeys(metadataKeys=False, fieldKeys=True):
            ctx.addAction(key, lambda key=key: self.packetlistmodel.addColumn(ColumnInfo(key, src="field"), addIdx))

        ctx.exec(self.packetlist.horizontalHeader().mapToGlobal(point))

    def getColumnInfoDefinition(self):
        return [
            ("key", "Key", "text", {"autocomplete":self.listObject.getAllKeys()}),
            ("title", "Column title", "text", {}),
            ("src", "Data source", "select", {"options":[("meta","Packet meta data"), ("field","Packet field")]}),
            ("show", "Display mode", "select", {"options":[ ("show","Display contents"), ("showname","Tree display contents"), ("hex","Hex value") ]}),
        ]

    def onAddColumn(self, insertBefore):
        par = showSettingsDlg(self.getColumnInfoDefinition())
        if par is not None:
            if par["title"] == "": par["title"] = par["key"]
            self.packetlistmodel.addColumn(ColumnInfo(**par), insertBefore)

    def onEditColumn(self, index):
        par = showSettingsDlg(self.getColumnInfoDefinition(), self.packetlistmodel.columns[index].toDict())
        if par is not None:
            if par["title"] == "": par["title"] = par["key"]
            self.packetlistmodel.removeColumn(index)
            self.packetlistmodel.addColumn(ColumnInfo(**par), index)

    def run_ndis(self):
        pass

    def addPacketToList(self, bbuf):
        idx = self.packetlist.rowCount()
        self.packetlist.insertRow(idx)
        c = 0
        #print(bbuf.ranges)
        for k,v in bbuf.metadata.items():
            #print(k,v)
            self.packetlist.setItem(idx, c, QTableWidgetItem(str(v)))
            c += 1
            if c > 10: break
        for rr in bbuf.ranges:
            #print(rr)
            self.packetlist.setItem(idx, c, QTableWidgetItem(str(rr.metadata)))
            c += 1
            if c > 10: break


@DataWidgetTypes.register(handles=ByteBuffer)
class ByteBufferWidget(QWidget):
    on_data_selected = pyqtSignal(QObject)
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
        self.textbox = HexView2()
        self.textbox.on_data_selected.connect(self.on_data_selected.emit)
        self.textbox.onNewSubflowCategory.connect(self.newSubflowCategory)
        self.textbox.formatInfoUpdated.connect(self.onFormatInfoUpdated)
        self.tabWidget.addTab(self.textbox, "Raw buffer")
        #layout.addWidget(toolbar)

    def setContents(self, bufObj):
        self.bufferObject = bufObj
        self.setWindowTitle(str(bufObj))
        self.textbox.setBuffer(bufObj)
        self.bufferObject.on_new_data.connect(self.onNewData)

    def onFormatInfoUpdated(self):
        self.tabWidget.clear()
        self.tabWidget.addTab(self.textbox, "Raw buffer")

    def newSubflowCategory(self, category, parse_context):
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == category:
                break
        widget = PacketListWidget()
        widget.setContents(parse_context.subflow_categories[category])
        self.tabWidget.addTab(widget, category)
        widget.on_data_selected.connect(self.on_data_selected.emit)

    def onNewData(self):
        #self.textbox.showHex(bufObj.buffer)
        self.textbox.redraw()

    def splitIntoPackets(self):
        pass

    def run_ndis(self):
        pass


class DynamicDataWidget(QWidget):
    on_data_selected = pyqtSignal(QObject)

    def __init__(self, *args):
        super().__init__(*args)
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
            self.setErrMes("Data is 'None'")
        else:
            if hasattr(data, "metadata"):
                self.metadataWidget.setContents(data.metadata)
            else:
                self.metadataWidget.setContents(None)
            widgetTyp, _ = DataWidgetTypes.find(handles=typ)
            if widgetTyp == None:
                self.setErrMes("Unknown data type "+str(typ))
            else:
                self.loadChildType(widgetTyp)
                self.childWidget.setContents(data)

    def setErrMes(self, msg="", title="Error"):
        self.loadChildType(QTextEdit)
        self.childWidget.setHtml("<h4>"+title+"</h4><pre>"+cgi.escape(msg)+"</pre>")

    def onDataSelected(self, data):
        self.on_data_selected.emit(data)

    def loadChildType(self, childType):
        if isinstance(self.childWidget, childType): return
        if self.childWidget != None:
            self.layout().removeWidget(self.childWidget)
            self.childWidget.setParent(None)
        self.childWidget = None  #neccessary, so if the next line throws, the error message will be shown
        self.childWidget = childType()
        try:
            self.childWidget.on_data_selected.connect(self.onDataSelected)
        except:
            print(str(childType)+" has no on_data_selected signal")
        self.layout().addWidget(self.childWidget,66)
