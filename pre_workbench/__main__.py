import os.path
import sys

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen

from pre_workbench import configs
from pre_workbench.mainwindow import WorkbenchMain
from pre_workbench.syshelper import load_file_watch


def run_app():
	from PyQt5.QtWidgets import QApplication

	app = QApplication(sys.argv)
	splashimg = configs.respath("icons/splash.jpg")
	splash = QSplashScreen(QPixmap(splashimg))
	splash.show()
	configs.registerOption("AppTheme", "fusion", lambda key, value: app.setStyle(value))
	load_file_watch(app, os.path.join(os.path.dirname(__file__), "stylesheet.css"), lambda contents: app.setStyleSheet(contents))
	ex = WorkbenchMain()
	ex.show()
	splash.finish(ex)
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())


run_app()


