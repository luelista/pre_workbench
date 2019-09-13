from PyQt5.QtWidgets import QApplication

def setClipboardText(txt):
    cb = QApplication.clipboard()
    cb.clear(mode=cb.Clipboard )
    cb.setText(txt, mode=cb.Clipboard)

def getClipboardText():
    cb = QApplication.clipboard()
    return cb.text(mode=cb.Clipboard)


def qApp():
    return QApplication.instance()
