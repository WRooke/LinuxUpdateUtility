# Intended to be "glue" that pulls GUI and main code file together
# See the following web pages for more information
# Figure out way to close child window, to close progress bar once kernel is finished downloading

# https://stackoverflow.com/questions/8630749/applying-python-functions-directly-to-qt-designer-as-signals
# https://doc.qt.io/qtforpython/tutorials/basictutorial/uifiles.html
# https://stackoverflow.com/questions/3196353/pyqt4-file-select-widget/3219438
# https://stackoverflow.com/questions/45688873/pyqt5-click-menu-and-open-new-window
#
# UI -> PY CONSOLE COMMAND
# python -m PyQt5.uic.pyuic -x [FILENAME].ui -o [FILENAME].py


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication
from PyQt5.QtCore import QObject, pyqtSlot
from GUI import Ui_Dialog
from Progress import Ui_Dialog as ProgressDialog
from PopUp import Ui_PopUpDialog
from Updater import runUpdate, InvalidDir
import sys, docx
import time
import os
import serial.tools.list_ports
import serial
import paramiko
from threading import Thread

class IPException(Exception):
  pass
class PathException(Exception):
  pass

class PopUpClass (QDialog, Ui_PopUpDialog):
  def __init__(self, parent=None):
    super(PopUpClass, self).__init__(parent)
    super().setupUi(self)

class ProgressClass (QDialog, ProgressDialog):
  def __init__(self, parent=None):
    super(ProgressClass, self).__init__(parent)
    super().setupUi(self)

class MainWindowUIClass( Ui_Dialog ):
  def __init__( self ):
    '''Initialize the super class
    '''
    super().__init__()

  def setupUi( self, MW ):
    ''' Setup the UI of the super class, and add here code
    that relates to the way we want our UI to operate.
    '''
    super().setupUi( MW )
    self.fileSelect.clicked.connect(self.fileOpen)
    # self.goButton.clicked.connect(self.generate)
    self.goButton.clicked.connect(self.threadGo)
    self.COMPort.view().pressed.connect(self.populateComPort)
    self.populateComPort()

  def populateComPort(self):
    count = 0
    for comport in serial.tools.list_ports.comports():
      self.COMPort.addItem("")
      self.COMPort.setItemText(count, QtWidgets.QApplication.translate("Dialog", comport.device))
      count += 1

  def fileOpen(self):
    qfd = QFileDialog()
    filePath = QFileDialog.getExistingDirectory(qfd, str("Open Linux kernel location"), os.getcwd())
    self.pathEdit.setText(filePath)

  def generate(self):
    print('load process started')
    self.goButton.setEnabled(False)
    try:
      if self.conIP.text() == "" or self.PCIP.text() == "":
        raise IPException
      if self.pathEdit.text() == "":
        raise PathException
      if runUpdate(self.COMPort.currentText(),self.conIP.text(),self.PCIP.text(), self.pathEdit.text()):
        cheese = QApplication.topLevelWidgets()
        print(cheese)
        self.popup("Kernel loaded successfully", "Success")
    except IPException:
      self.popup("IP address missing\nPlease try again","Error")
    except PathException:
      self.popup("Kernel path missing\nPlease try again","Error")
    except serial.SerialException:
      self.popup("Serial port in use\nClose the port and try again","Error")
    except paramiko.ssh_exception.SSHException:
      self.popup("Could not connect through SSH\nEnsure the IP address of the controller is correct\nand that is is connected correctly", "Error")
    except InvalidDir:
      self.popup("Directory does not contain Linux Kernel files", "Error")

    self.goButton.setEnabled(True)

  def threadGo(self):
    self.progProc = Thread(target=self.progressInd,args=())
    self.genProc = Thread(target=self.generate,args=())
    self.progProc.start()
    self.genProc.start()

  def popup(self, errorMessage,windowTitle):
    widget = PopUpClass()
    widget.popuptext.setText(errorMessage)
    widget.setWindowTitle(windowTitle)
    widget.exec_()

  def progressInd(self):
    widget = ProgressClass()
    widget.exec_()

if __name__ == '__main__':

  app = QtWidgets.QApplication(sys.argv)
  MainWindow = QtWidgets.QMainWindow()
  ui = MainWindowUIClass()
  ui.setupUi(MainWindow)
  MainWindow.show()
  sys.exit(app.exec_())
