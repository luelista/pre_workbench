#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
ZetCode PyQt5 tutorial 

This program creates a skeleton of
a classic GUI application with a menubar,
toolbar, statusbar, and a central widget. 

Author: Jan Bodnar
Website: zetcode.com 
Last edited: August 2017
"""

import sys
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, \
    QFileDialog, QTabWidget, QTableWidget, QWidget, QToolBar, QVBoxLayout,\
    QMdiArea, QFormLayout, QToolBox, QComboBox, QLineEdit, QCheckBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QObject)

from objects import ByteBuffer, ByteBufferList, ReloadRequired
from datasource import PcapFileDataSource, FileDataSource, LiveCaptureDataSource
import configs
from widgets import ExpandWidget, SettingsGroup

DataSourceTypes = [PcapFileDataSource, FileDataSource, LiveCaptureDataSource]
def getDataSourceList():
    return [(dt.__name__, dt.DisplayName) for dt in DataSourceTypes]
def getDataSourceByType(typename):
    for dt in DataSourceTypes:
        if dt.__name__ == typename:
            return dt

class Example(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
        
    def initUI(self):               
        
        self.mdiArea = QMdiArea()
        self.setCentralWidget(self.mdiArea)

        exitAct = QAction('Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(self.close)

        newAct = QAction('New window', self)
        newAct.setShortcut('Ctrl+N')
        newAct.setStatusTip('New window')
        newAct.triggered.connect(self.onFileNewWindowAction)

        openAct = QAction('Open', self)
        openAct.setShortcut('Ctrl+O')
        openAct.setStatusTip('Open file')
        openAct.triggered.connect(self.onFileOpenAction)

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAct)
        fileMenu.addAction(exitAct)

        toolbar = self.addToolBar('Main')
        toolbar.addAction(newAct)
        toolbar.addAction(openAct)
        toolbar.addAction(exitAct)
        
        self.setGeometry(300, 300, 850, 850)
        self.setWindowTitle('Main window')    
        self.show()

    def onFileNewWindowAction(self):
        ow = ObjectWindow()
        ow.setConfig({})
        self.mdiArea.addSubWindow(ow)
        ow.show()


    def onFileOpenAction(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", configs.getValue("lastOpenFile",""),"All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            configs.setValue("lastOpenFile", fileName)
            self.openFile(fileName)
    
    def openFile(self, fileName):
        if fileName.endswith(".pcap") or fileName.endswith(".pcapng"):
            meta = {
                "name": fileName,
                "dataSourceType": "PcapFilePacketList",
                "fileName": fileName
            }
        else:
            meta = {
                "name": fileName,
                "dataSourceType": "FileByteBuffer",
                "fileName": fileName
            }
        ow = ObjectWindow()
        ow.setConfig(meta)
        self.mdiArea.addSubWindow(ow)
        ow.show()



class ObjectWindow(QWidget):
    def __init__(self, name="Untitled", dataSourceType=None):
        super().__init__()
        self.params = {"name": name, "dataSourceType": dataSourceType}
        self.dataSource = None
        self.dataSourceType = None
        self.initUI()
        
    def initUI(self):
        layout=QVBoxLayout()
        self.setLayout(layout)
        #tb = QToolBox(self)
        #layout.addWidget(tb)
        self.metaConfig = SettingsGroup([
            ("name", "Name", "text", {}),
            ("dataSourceType", "Data Source Type", "select", {"options":getDataSourceList()}),
        ])
        self.metaConfig.item_changed.connect(self.onConfigChanged)
        #tb.addItem(self.metaConfig, "Metadata")
        layout.addWidget(ExpandWidget("Metadata", self.metaConfig))

        self.sourceConfig = SettingsGroup([])
        self.sourceConfig.item_changed.connect(self.onConfigChanged)
        #tb.addItem(self.sourceConfig, "Data Source Options")
        layout.addWidget(ExpandWidget("Data Source Options", self.sourceConfig))

        self.dataDisplay = QWidget()
        #tb.addItem(self.dataDisplay, "Results")
        layout.addWidget(ExpandWidget("Results", self.dataDisplay))

    def setConfig(self, config):
        self.metaConfig.setValues(config)
        self.sourceConfig.setValues(config)
        self.params.update(config)
        self.loadDataSource()

    def onConfigChanged(self, key, value):
        self.params[key] = value
        if key == "dataSourceType":
            self.loadDataSource()
        else:
            if self.dataSource != None:
                try:
                    self.dataSource.updateParam(key, value)
                except ReloadRequired as ex:
                    self.loadDataSource()

    def loadDataSource(self):
        if not self.params["dataSourceType"]: return
        clz = getDataSourceByType(self.params["dataSourceType"])
        if self.dataSourceType != self.params["dataSourceType"]:
            self.sourceConfig.setFields(clz.ConfigFields)
            self.sourceConfig.setValues(self.params)
            self.dataSourceType = self.params["dataSourceType"]
        self.dataSource = clz(self.params)





class PacketListWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
        
    def initUI(self):
        toolbar = QToolBar()
        self.cancelAction = toolbar.addAction("Cancel")
        self.cancelAction.triggered.connect(self.onCancelFetch)
        self.reloadAction = toolbar.addAction("Reload")
        self.reloadAction.triggered.connect(self.reload)

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        layout.setMenuBar(toolbar)
        layout.addWidget(tabs)
        
        self.packetlist = QTableWidget()
        tabs.addTab(self.packetlist, "Raw Frames")

        self.iplist = QTableWidget()
        tabs.addTab(self.iplist, "IP Payloads")

        self.udplist = QTableWidget()
        tabs.addTab(self.udplist, "UDP Payloads")

        self.sessionlist = QTableWidget()
        tabs.addTab(self.sessionlist, "TCP Sessions")

    def setPacketList(self, lstObj):
        self.listObject = lstObj
        self.setWindowTitle(str(lstObj))
        self.listObject.on_new_packet.connect(self.onNewPacket)
        self.listObject.on_finished.connect(self.onFinished)

    def onNewPacket(self):
        pass

    def onFinished(self):
        self.cancelAction.setEnabled(False)

    def onCancelFetch(self):
        self.listObject.cancelFetch()

    def reload(self):
        self.listObject.startFetch()

    def run_ndis(self):
        pass



class ByteBufferWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
        
    def initUI(self):
        toolbar = QToolBar()
        self.cancelAction = toolbar.addAction("Cancel")
        self.cancelAction.triggered.connect(self.onCancelFetch)
        self.reloadAction = toolbar.addAction("Reload")
        self.reloadAction.triggered.connect(self.reload)
        self.splitIntoPacketsAction = toolbar.addAction("Split into packets")
        self.splitIntoPacketsAction.triggered.connect(self.splitIntoPackets)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.textbox = QTextEdit()
        layout.setMenuBar(toolbar)
        layout.addWidget(self.textbox)
        

    def setByteBuffer(self, bufObj):
        self.bufferObject = bufObj
        self.setWindowTitle(str(bufObj))
        self.textbox.setText(bufObj.toHexDump())
        self.bufferObject.on_new_data.connect(self.onNewData)
        self.bufferObject.on_finished.connect(self.onFinished)

    def onNewData(self):
        self.textbox.setText(self.bufferObject.toHexDump())

    def onFinished(self):
        self.cancelAction.setEnabled(False)

    def onCancelFetch(self):
        self.bufferObject.cancelFetch()

    def reload(self):
        self.bufferObject.startFetch()

    def run_ndis(self):
        pass




if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())