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


from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from GUI import Ui_Dialog
from Progress import Ui_Form as ProgressDialog
from PopUp import Ui_PopUpDialog
# from Updater import runUpdate, InvalidDir
import sys
import time
import os
import serial.tools.list_ports
import serial
import paramiko
from threading import Thread
from multiprocessing import Process
import re
import tftpy

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

  def handleChange(self,UpdateText,UpdateNum):
    self.Status.setText(UpdateText)
    self.progressBar.setValue(UpdateNum)

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
  loadStatus = pyqtSignal(str,int)

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
    self.goButton.setEnabled(False)
    try:
      if self.conIP.text() == "" or self.PCIP.text() == "":
        raise IPException
      if self.pathEdit.text() == "":
        raise PathException
      if self.runUpdate(self.COMPort.currentText(),self.conIP.text(),self.PCIP.text(), self.pathEdit.text()):
        self.loadStatus.emit("Completed!", 10)
        self.popup("Kernel loaded successfully", "Success")
        popupThread = Thread(target=self.popup,args=(self,"Kernel loaded successfully", "Success"))
        popupThread.start()
    except IPException:
      # self.popup("IP address missing\nPlease try again","Error")
      popupThread = Thread(target=self.popup, args=(self, "Kernel loaded successfully", "Success"))
      popupThread.start()
    except PathException:
      # self.popup("Kernel path missing\nPlease try again","Error")
      popupThread = Thread(target=self.popup, args=("Kernel loaded successfully", "Success"))
      popupThread.start()
    except serial.SerialException:
      # self.popup("Serial port in use\nClose the port and try again","Error")
      # popupThread = Thread(target=self.popup, args=("Kernel loaded successfully", "Success"))
      # popupThread.daemon = True
      self.popup("Serial port in use\nClose the port and try again", "Error")
      # self.genProc.join()
      # popupThread.start()
    except paramiko.ssh_exception.SSHException:
      # self.popup("Could not connect through SSH\nEnsure the IP address of the controller is correct\nand that is is connected correctly", "Error")
      popupThread = Thread(target=self.popup, args=(self, "Kernel loaded successfully", "Success"))
      popupThread.start()
    except InvalidDir:
      self.popup("Directory does not contain Linux Kernel files", "Error")
      popupThread = Thread(target=self.popup, args=(self, "Kernel loaded successfully", "Success"))
      popupThread.start()

    self.goButton.setEnabled(True)

  def threadGo(self):
    self.progProc = Thread(target=self.progressInd,args=())
    self.genProc = Thread(target=self.generate,args=())
    self.genProc.daemon = True
    self.progProc.daemon = True
    self.progProc.start()
    time.sleep(1)
    self.genProc.start()

  def popup(self, errorMessage,windowTitle):
    widget = PopUpClass()
    widget.popuptext.setText(errorMessage)
    widget.setWindowTitle(windowTitle)
    widget.exec_()

  def progressInd(self):
    widget = ProgressClass()
    self.loadStatus.connect(widget.handleChange)
    widget.exec_()

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

  def runUpdate(self, comPort, conIP, PCIP, kernelPath):
    self.loadStatus.emit("Loading started",0)
    print(kernelPath)
    newpath = kernelPath.replace('/', '\\')
    if os.path.isfile(os.path.join(newpath, 'ubifs.img')) and os.path.isfile(os.path.join(newpath, 'flash_mmc.img')) and os.path.isfile(os.path.join(newpath, 'flash_eth.img')) and os.path.isfile(os.path.join(newpath, 'flash_blk.img')) and os.path.isfile(os.path.join(newpath, 'configblock.bin')):
      pass
    else:
      raise InvalidDir
    self.loadStatus.emit("Starting TFTP server", 1)
    serverino = ServerClass(newpath)
    tftpProcess = Thread(target=serverino.ServerFunc, args=())
    tftpProcess.start()
    self.loadStatus.emit("Opening COM Port",1)
    ser = serial.Serial(comPort, 115200, timeout=0.1)
    ser.close()
    ser.open()
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

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    self.sendTilde(ser)

    self.writeCommand(ser, update1)
    self.writeCommand(ser, update2)
    self.writeCommand(ser, update3)
    self.writeCommand(ser, update4)
    ser.write(update5.encode())
    self.loadStatus.emit("Downloading over TFTP", 5)
    while 1:
      out = ser.readline().decode()
      matchUpdate = re.search('enter "run update"*.', out)
      if matchUpdate:
        ser.write(update6.encode())
        break
    self.loadStatus.emit("Rebooting", 7)
    while 1:
      out = ser.readline().decode()
      matchReset = re.search('resetting*.', out)
      if matchReset:
        self.sendTilde(ser)
        break

    print('sending boot command')
    self.writeCommand(ser, newline)
    self.writeCommand(ser, newline)
    self.writeCommand(ser, boot)

    while 1:
      out = ser.readline().decode()
      matchLogin = re.search('.*iecTeso version.*', out)
      if matchLogin:
        for i in range(10):
          out = ser.readline().decode()

        ser.write(newline.encode())
        for i in range(10):
          out = ser.readline().decode()
        break

    self.loadStatus.emit("Logging in", 8)
    self.writeCommand(ser, 'root\n')
    self.writeCommand(ser, 'Netsilicon\n')
    configstr = "ifconfig eth0 " + conIP + "\n"
    self.writeCommand(ser, configstr)
    self.loadStatus.emit("Finishing up", 9)
    ser.close()
    serverino.ServerKill()
    return True

if __name__ == '__main__':

  app = QtWidgets.QApplication(sys.argv)
  MainWindow = QtWidgets.QMainWindow()
  ui = MainWindowUIClass()
  ui.setupUi(MainWindow)
  MainWindow.show()
  sys.exit(app.exec_())
