import cgi

from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, \
    QFileDialog, QTabWidget, QTableWidget, QWidget, QToolBar, QVBoxLayout, \
    QMdiArea, QFormLayout, QToolBox, QComboBox, QLineEdit, QCheckBox, QLabel, QTableWidgetItem, QMenu, \
    QAbstractItemView, QDialog, qApp, QTableView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QObject, QSize, QAbstractItemModel, QModelIndex)

from objects import ByteBuffer, ByteBufferList, ReloadRequired
from datasource import PcapFileDataSource, FileDataSource, LiveCaptureDataSource
import configs
from genericwidgets import ExpandWidget, SettingsGroup, printsizepolicy, showSettingsDlg
from hexview import HexView2
from typeregistry import DataWidgetTypes

class ColumnInfo:
    def __init__(self, title, key=None, src="field", show="show"):
        self.title=title
        if key == None: key = title
        self.key = key
        self.src = src
        self.show=show
    def extract(self, bbuf : ByteBuffer):
        if self.src == "field":
            rr = bbuf.fields.get(self.key)
            if rr == None: return None
            if self.show == "hex":
                return bbuf.toHex(rr.start, rr.length(), " ")
            else:
                return rr.metadata[self.show]
        elif self.src == "meta":
            return bbuf.metadata.get(self.key)
        else:
            return None
    def __str__(self):
        return self.title
    def __repr__(self):
        return "ColumnInfo(%s, %s, %s, %s)" % (self.title, self.key, self.src, self.show)
    def toDict(self):
        return {"title":self.title, "key":self.key, "src":self.src, "show":self.show}


class PacketListModel(QAbstractItemModel):
    def __init__(self, plist, parent=None):
        super().__init__(parent)
        self.listObject = plist
        plist.on_new_packet.connect(self.onNewPacket)
        self.columns = [ColumnInfo("frame.time", src="meta"), ColumnInfo("frame.len", src="meta"), ColumnInfo("frame.number", src="meta"), ColumnInfo("frame.protocols", src="meta"),
                        ColumnInfo("eth.src"), ColumnInfo("eth.dst"), ColumnInfo("eth.type"),
                        ColumnInfo("ip.src"), ColumnInfo("ip.dst"), ColumnInfo("ip.proto"),
                        ColumnInfo("Payload", key="tcp.payload", show="hex")]
        #self.rootItem = TreeItem(("Model", "Status","Location"))

    def onNewPacket(self):
        idx = len(self.listObject) - 1
        print("onNewPacket",idx)
        self.beginInsertRows(QModelIndex(), idx, idx)
        self.endInsertRows()

    def columnCount(self, parent):
        return len(self.columns)

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole:
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
        self.setLayout(layout)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        #self.packetlist = QTableWidget()
        #self.packetlist.setColumnCount(10)
        self.packetlist = QTableView()
        self.packetlist.setContextMenuPolicy(Qt.CustomContextMenu)
        self.packetlist.customContextMenuRequested.connect(self.onPacketlistContextMenu)
        self.packetlist.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.packetlist.horizontalHeader().customContextMenuRequested.connect(self.onHeaderContextMenu)
        self.packetlist.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabs.addTab(self.packetlist, "Raw Frames")

        self.iplist = QTableWidget()
        tabs.addTab(self.iplist, "IP Payloads")

        self.udplist = QTableWidget()
        tabs.addTab(self.udplist, "UDP Payloads")

        self.sessionlist = QTableWidget()
        tabs.addTab(self.sessionlist, "TCP Sessions")

    def setContents(self, lstObj):
        self.listObject = lstObj
        print("setContents", lstObj, len(lstObj))
        self.setWindowTitle(str(lstObj))
        #for bbuf in lstObj.buffers:
        #    self.addPacketToList(bbuf)
        self.packetlistmodel = PacketListModel(self.listObject)
        self.packetlist.setModel(self.packetlistmodel)
        self.packetlist.selectionModel().selectionChanged.connect(self.onPacketlistSelectionChanged)
        self.packetlist.selectionModel().currentChanged.connect(self.onPacketlistCurrentChanged)

    def onPacketlistSelectionChanged(self, selected, deselected):
        pass
    def onPacketlistCurrentChanged(self, current, previous):
        if current.isValid():
            bbuf = self.listObject.buffers[current.row()]
            print("currentChanged",bbuf)
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
        ctx.addAction("Add column ...", lambda: self.onAddColumn(None if index == -1 else index))

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
        toolbar = QToolBar()
        self.splitIntoPacketsAction = toolbar.addAction("Split into packets")
        self.splitIntoPacketsAction.triggered.connect(self.splitIntoPackets)

        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.textbox = HexView2()
        layout.addWidget(self.textbox)
        layout.addWidget(toolbar)


    def setContents(self, bufObj):
        self.bufferObject = bufObj
        self.setWindowTitle(str(bufObj))
        self.textbox.setBuffer(bufObj)
        self.bufferObject.on_new_data.connect(self.onNewData)

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
        self.childWidget = None
        self.setErrMes("No data loaded")
    def setContents(self, data):
        typ = type(data)
        if data is None:
            self.setErrMes("Data is 'None'")
        else:
            widgetTyp = DataWidgetTypes.find(handles=typ)
            if widgetTyp == None:
                self.setErrMes("Unknown data type "+str(typ))
            else:
                self.loadChildType(widgetTyp)
                self.childWidget.setContents(data)

    def setErrMes(self, msg):
        self.loadChildType(QTextEdit)
        self.childWidget.setHtml("<h4>Error</h4><pre>"+cgi.escape(msg)+"</pre>")

    def onDataSelected(self, data):
        self.on_data_selected.emit(data)

    def loadChildType(self, childType):
        if self.childWidget != None:
            self.layout().removeWidget(self.childWidget)
            self.childWidget.setParent(None)
        self.childWidget = childType()
        try:
            self.childWidget.on_data_selected.connect(self.onDataSelected)
        except:
            print(str(childType)+" has no on_data_selected signal")
        self.layout().addWidget(self.childWidget)
