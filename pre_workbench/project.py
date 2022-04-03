import json
import os
import sqlite3

from pre_workbench.rangetree import InteractiveFormatInfoContainer
from pre_workbench.structinfo import xdrm

class ProjectFormatInfoContainer(InteractiveFormatInfoContainer):
    def write_file(self, fileName):
        self.project.setValue("format_infos", self.to_text())
        self.updated.emit()

class Project:
    def __init__(self, dirName):
        self.projectFolder = dirName
        self.projectDbFile = os.path.join(dirName, ".pre_workbench")
        self.db = sqlite3.connect(self.projectDbFile)
        self.initDb()
        self.formatInfoContainer = ProjectFormatInfoContainer(load_from_string=self.getValue("format_infos", "DEFAULT struct(endianness=\"<\") {}"))
        self.formatInfoContainer.project = self
        #self.formatInfoContainer = InteractiveFormatInfoContainer(load_from_string=self.getValue("format_info_file", ""))

    def getRelativePath(self, absolutePath):
        path = os.path.relpath(absolutePath, self.projectFolder)
        if path.startswith(".."):
            return absolutePath
        else:
            return path

    def initDb(self):
        cur = self.db.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS annotations (rowid INTEGER PRIMARY KEY, set_name TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL, meta TEXT NOT NULL);
        ''')
        cur.execute('''
        CREATE TABLE IF NOT EXISTS options (name TEXT PRIMARY KEY, value BLOB NOT NULL);
        ''')

    def getValue(self, key, defaultValue=None):
        cur = self.db.cursor()
        cur.execute("SELECT value FROM options WHERE name = ?", (key,))
        result = cur.fetchone()
        if result:
            return xdrm.loads(result[0])
        else:
            return defaultValue

    def setValue(self, key, value):
        cur = self.db.cursor()
        cur.execute("REPLACE INTO options  (`name`, value) VALUES (?,?)", (key, xdrm.dumps(value)))
        self.db.commit()


    def getAnnotationSetNames(self):
        cur = self.db.cursor()
        cur.execute("SELECT DISTINCT set_name FROM annotations")
        return [x[0] for x in cur.fetchall()]

    def getAnnotations(self, set_name):
        cur = self.db.cursor()
        cur.execute("SELECT rowid, start, end, meta FROM annotations WHERE set_name = ?", (set_name,))
        return cur.fetchall()

    def storeAnnotation(self, set_name, range):
        cur = self.db.cursor()
        if 'rowid' in range.metadata:
            cur.execute('''REPLACE INTO annotations (rowid, set_name, start, end, meta) VALUES (?,?,?,?,?)''',
                        (range.metadata['rowid'], set_name, range.start, range.end, json.dumps(range.metadata)))
        else:
            cur.execute('''INSERT INTO annotations (set_name, start, end, meta) VALUES (?,?,?,?)''',
                        (set_name, range.start, range.end, json.dumps(range.metadata)))
        self.db.commit()
        range.metadata['rowid'] = cur.lastrowid

