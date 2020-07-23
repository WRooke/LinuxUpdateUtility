import paramiko
import serial
import re
import tftpy
import time
from multiprocessing import Process
from os import path

class InvalidDir(Exception):
  pass

def ServerFunc(ServerPath):
  server = tftpy.TftpServer(ServerPath)
  # server = tftpy.TftpServer(tftproot=r'C:\Users\williamr\OneDrive - OEM TECHNOLOGY SOLUTIONS PTY LTD\PC3\070-0767\-5\3-0899V2')
  server.listen()

def sendTilde(serialObject):
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

def writeCommand(serialObject, string):
  serialObject.write(string.encode())
  out = serialObject.readline().decode()
  time.sleep(0.2)

def runUpdate(comPort, conIP, PCIP, kernelPath):
  print(kernelPath)
  newpath = kernelPath.replace('/','\\')
  if path.isfile(path.join(newpath, 'ubifs.img')) and path.isfile(path.join(newpath, 'flash_mmc.img')) and path.isfile(path.join(newpath, 'flash_eth.img')) and path.isfile(path.join(newpath, 'flash_blk.img')) and path.isfile(path.join(newpath, 'configblock.bin')):
    pass
  else:
    raise InvalidDir
  tftpProcess = Process(target=ServerFunc, args=(newpath,))
  tftpProcess.start()
  ser = serial.Serial(comPort, 115200, timeout=0.1)
  ser.close()
  ser.open()
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  client.connect(conIP, username='root', password='Netsilicon')
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

  sendTilde(ser)

  writeCommand(ser, update1)
  writeCommand(ser, update2)
  writeCommand(ser, update3)
  writeCommand(ser, update4)
  ser.write(update5.encode())
  while 1:
    out = ser.readline().decode()
    matchUpdate = re.search('enter "run update"*.', out)
    if matchUpdate:
      ser.write(update6.encode())
      break

  while 1:
    out = ser.readline().decode()
    matchReset = re.search('resetting*.', out)
    if matchReset:
      sendTilde(ser)
      break

  print('sending boot command')
  writeCommand(ser, newline)
  writeCommand(ser, newline)
  writeCommand(ser, boot)

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

  print('logging in')
  writeCommand(ser, 'root\n')
  writeCommand(ser, 'Netsilicon\n')
  configstr = "ifconfig eth0 " + conIP + "\n"
  writeCommand(ser, configstr)

  ser.close()
  tftpProcess.terminate()
  return True

if __name__ == '__main__':
  runUpdate()