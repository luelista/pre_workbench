from PyQt5.QtWidgets import QApplication

from typeregistry import TypeRegistry

NavigateCommands = dict()

def setClipboardText(txt):
    cb = QApplication.clipboard()
    cb.clear(mode=cb.Clipboard )
    cb.setText(txt, mode=cb.Clipboard)

def getClipboardText():
    cb = QApplication.clipboard()
    return cb.text(mode=cb.Clipboard)

def splitNavArgs(args):
    start = None
    for i in range(len(args)):
        if not "=" in args[i]:
            if start is not None:
                yield args[start:i]
            start = i
    if start is not None:
        yield args[start:]


def navigate(*args):
    for item in splitNavArgs(args):
        navigateSingle(*item)

def navigateSingle(cmd, *args):
    fun = NavigateCommands[cmd]
    params = dict()
    for arg in args:
        key, value = arg.split("=", 2)
        params[key] = value
    fun(**params)

def qApp():
    return QApplication.instance()
