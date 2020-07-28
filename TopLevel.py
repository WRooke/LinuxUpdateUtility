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


import os
import re
import sys
import time
from threading import Thread
import ipaddress

import paramiko
import serial
import serial.tools.list_ports
import tftpy
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from PyQt5.QtWidgets import QFileDialog, QDialog

from GUI import Ui_Dialog
from PopUp import Ui_PopUpDialog
from Progress import Ui_Form as ProgressDialog


class IPException(Exception):
  pass
class PathException(Exception):
  pass

class PopUpClass (QDialog, Ui_PopUpDialog):
  def __init__(self, parent=None):
    super(PopUpClass, self).__init__(parent)
    super().setupUi(self)
  def handleError(self,WindowTitle,ErrorMess):
    self.popuptext.setText(ErrorMess)
    self.setWindowTitle(WindowTitle)
  def Opener(self):
    self.show()
  def Closer(self):
    self.hide()

class ProgressClass (QDialog, ProgressDialog):
  def __init__(self, parent=None):
    super(ProgressClass, self).__init__(parent)
    super().setupUi(self)

  def handleChange(self,UpdateText,UpdateNum):
    self.Status.setText(UpdateText)
    self.progressBar.setValue(UpdateNum)
  def Closer(self):
    self.hide()
  def Opener(self):
    self.show()

class UpdateThread(QThread):
  loadStatus = pyqtSignal(str, int)
  closeProg = pyqtSignal()
  errorMessage = pyqtSignal(str,str)
  loadPopup = pyqtSignal()
  openProg = pyqtSignal()
  def __init__(self, COMPort, conIP, PCIP, pathEdit):
    QThread.__init__(self)
    self.COMPort = COMPort
    self.conIP = conIP
    self.PCIP = PCIP
    self.pathEdit = pathEdit


  def run(self):
    try:
      ser = serial.Serial(self.COMPort, 115200, timeout=0.1)
      ser.close()
      self.runUpdate(ser,self.conIP,self.PCIP,self.pathEdit)
      self.errorMessage.emit("Success", "Kernel loaded successfully\nController IP address is: " + self.conIP)
      self.loadPopup.emit()
      self.closeProg.emit()
      self.quit()
    except PathException:
      ser.close()
      self.errorMessage.emit("Error", "Please select a directory")
      self.loadPopup.emit()
      self.closeProg.emit()
    except serial.SerialException:
      self.errorMessage.emit("Error", "Cannot open serial port\nPlease ensure no other program is using the serial port\nand that it is connected correctly")
      self.loadPopup.emit()
      self.closeProg.emit()
    except paramiko.ssh_exception.SSHException:
      ser.close()
      self.errorMessage.emit("Error", "Cannot connect to controller through SSH\nPlease ensure controller is connected correctly")
      self.loadPopup.emit()
      self.closeProg.emit()
    except InvalidDir:
      ser.close()
      self.errorMessage.emit("Error", "Directory does not contain Linux Kernel files\nPlease select a new directory")
      self.loadPopup.emit()
      self.closeProg.emit()
    except ipaddress.AddressValueError:
      ser.close()
      self.errorMessage.emit("Error", "IP address not valid\nPlease enter a valid IP")
      self.loadPopup.emit()
      self.closeProg.emit()

  def sendTilde(self, serialObject):
    command = '~\n'
    query = 'version\n'
    newline = '\n'
    while 1:
      serialObject.write(command.encode())
      out = serialObject.readline()
      serialObject.write(query.encode())
      out = serialObject.readline()
      decoded = out.decode()
      match = re.search('Colibri VFxx*.', decoded)
      if match:
        for i in range(10):
          out = serialObject.readline().decode()

        serialObject.write(newline.encode())
        for i in range(10):
          out = serialObject.readline().decode()
        break

  def writeCommand(self, serialObject, string):
    serialObject.write(string.encode())
    out = serialObject.readline().decode()
    time.sleep(0.2)

  def runUpdate(self, serialObject, conIP, PCIP, kernelPath):
    test = ipaddress.IPv4Address(conIP)
    test = ipaddress.IPv4Address(PCIP)
    newpath = kernelPath.replace('/', '\\')
    if kernelPath == "":
      raise PathException
    if os.path.isfile(os.path.join(newpath, 'ubifs.img')) and os.path.isfile(
        os.path.join(newpath, 'flash_mmc.img')) and os.path.isfile(
        os.path.join(newpath, 'flash_eth.img')) and os.path.isfile(
        os.path.join(newpath, 'flash_blk.img')) and os.path.isfile(os.path.join(newpath, 'configblock.bin')):
      pass
    else:
      raise InvalidDir
    self.loadStatus.emit("Starting TFTP server", 1)
    serverino = ServerClass(newpath)
    tftpProcess = Thread(target=serverino.ServerFunc, args=())
    tftpProcess.start()
    self.loadStatus.emit("Opening COM Port", 1)
    serialObject.open()
    self.loadStatus.emit("Opening SSH connection", 2)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(conIP, username='root', password='Netsilicon')
    self.loadStatus.emit("Rebooting", 2)
    stdin, stdout, stderr = client.exec_command('reboot')

    client.close()

    boot = 'boot\n'
    update1 = "setenv serverip " + PCIP + "\n"
    update2 = "setenv ipaddr " + conIP + "\n"
    update3 = "setenv setupdate 'tftpboot ${loadaddr} ${serverip}:flash_eth.img && source ${loadaddr}'\n"
    update4 = "saveenv\n"
    update5 = "run setupdate\n"
    update6 = "run update\n"
    newline = '\n'
    out = ''

    serialObject.reset_input_buffer()
    serialObject.reset_output_buffer()

    self.sendTilde(serialObject)

    self.writeCommand(serialObject, update1)
    self.writeCommand(serialObject, update2)
    self.writeCommand(serialObject, update3)
    self.writeCommand(serialObject, update4)
    serialObject.write(update5.encode())

    while 1:
      out = serialObject.readline().decode()
      matchUpdate = re.search('enter "run update"*.', out)
      if matchUpdate:
        serialObject.write(update6.encode())
        break
    self.loadStatus.emit("Downloading over TFTP", 5)
    while 1:
      out = serialObject.readline().decode()
      matchReset = re.search('resetting*.', out)
      if matchReset:
        self.sendTilde(serialObject)
        break
    self.loadStatus.emit("Rebooting", 7)
    self.writeCommand(serialObject, newline)
    self.writeCommand(serialObject, newline)
    self.writeCommand(serialObject, boot)

    while 1:
      out = serialObject.readline().decode()
      matchLogin = re.search('.*iecTeso version.*', out)
      if matchLogin:
        for i in range(10):
          out = serialObject.readline().decode()

        serialObject.write(newline.encode())
        for i in range(10):
          out = serialObject.readline().decode()
        break

    self.loadStatus.emit("Logging in", 8)
    self.writeCommand(serialObject, 'root\n')
    self.writeCommand(serialObject, 'Netsilicon\n')
    configstr = "ifconfig eth0 " + conIP + "\n"
    self.writeCommand(serialObject, configstr)
    self.loadStatus.emit("Finishing up", 9)
    serialObject.close()
    serverino.ServerKill()
    self.closeProg.emit()
    return True

class InvalidDir(Exception):
  pass

class ServerClass(object):
  def __init__(self, ServerPath):
    self.ServerPath = ServerPath
    self.server = tftpy.TftpServer(self.ServerPath)
  def ServerFunc(self):
    self.server.listen()
  def ServerKill(self):
    self.server.stop()

class MainWindowUIClass( Ui_Dialog, QObject ):

  def __init__( self ):
    '''Initialize the super class
    '''
    super().__init__()
    self.progress = ProgressClass()
    self.popup = PopUpClass()

  def setupUi( self, MW ):
    ''' Setup the UI of the super class, and add here code
    that relates to the way we want our UI to operate.
    '''
    super().setupUi( MW )
    self.fileSelect.clicked.connect(self.fileOpen)
    # self.goButton.clicked.connect(self.generate)
    self.goButton.clicked.connect(self.generate)
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

    updaterThread = UpdateThread(self.COMPort.currentText(),self.conIP.text(),self.PCIP.text(), self.pathEdit.text())
    updaterThread.loadStatus.connect(self.progress.handleChange)
    updaterThread.openProg.connect(self.progress.Opener)
    updaterThread.closeProg.connect(self.progress.Closer)
    updaterThread.errorMessage.connect(self.popup.handleError)
    updaterThread.loadPopup.connect(self.popup.Opener)
    updaterThread.start()
    self.progress.exec_()
    self.popup.exec_()
    self.popup.hide()

if __name__ == '__main__':

  app = QtWidgets.QApplication(sys.argv)
  MainWindow = QtWidgets.QMainWindow()
  ui = MainWindowUIClass()
  ui.setupUi(MainWindow)
  MainWindow.show()
  sys.exit(app.exec_())
