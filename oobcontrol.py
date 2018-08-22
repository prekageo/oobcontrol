#!/usr/bin/env python

import ConfigParser
import cookielib
import ctypes
import os.path
import re
import ssl
import subprocess
import sys
import urllib2
import xml.dom.minidom

def java(params):
  try:
    ctypes.cdll.kernel32.FreeConsole()
  except OSError:
    pass
  # http://bugs.python.org/issue25492
  subprocess.Popen('%s %s' % (config.params.java, params), shell = True, stdin = open(os.devnull, 'r'), stdout = open(os.devnull, 'w'), stderr = open(os.devnull, 'w'))

class Base:
  def __init__(self, hostname, username, password):
    self.hostname = hostname
    self.username = username
    self.password = password

  def check_for_missing_jars(self):
    if os.path.exists(os.path.basename(self.FILES[0])):
      return

    msg = 'Missing JARs. Try to download these:\n'
    for file in self.FILES:
      msg += 'wget http://%s%s\n' % (self.hostname, file)
    error(msg)

class Idrac(Base):
  FILES = [
    '/software/avctKVM.jar',
    '/software/avctKVMIOLinux32.jar',
    '/software/avctKVMIOLinux64.jar',
    '/software/avctKVMIOMac64.jar',
    '/software/avctKVMIOWin32.jar',
    '/software/avctKVMIOWin64.jar',
    '/software/avctVMLinux32.jar',
    '/software/avctVMLinux64.jar',
    '/software/avctVMMac64.jar',
    '/software/avctVMWin32.jar',
    '/software/avctVMWin64.jar',
  ]

  def console(self):
    self.check_for_missing_jars()
    java('-cp avctKVM.jar com.avocent.idrac.kvm.Main ip=%s user=%s passwd=%s kmport=5900 vport=5900 apcp=1' % (self.hostname, self.username, self.password))

  def _login(self):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    cj = cookielib.CookieJar()
    self.opener = urllib2.build_opener(urllib2.HTTPSHandler(context = context), urllib2.HTTPCookieProcessor(cj))
    
    f = self.opener.open('https://%s/data/login' % self.hostname, 'user=%s&password=%s' % (self.username, self.password))
    data = f.read()
    forward_url = re.search(r'forwardUrl>([^<]*)', data)
    if forward_url is None:
      error('Cannot login')
    forward_url = forward_url.group(1)

    token_name = re.search(r',([^=]*)', forward_url).group(1)
    token_value = re.search(r'([^=]*)$', forward_url).group(1)
    self.opener.addheaders.append((token_name, token_value))
    
  def reboot(self):
    try:
      self._login()
      f = self.opener.open('https://%s/data?set=pwState:3' % self.hostname, '')
      data = f.read()
      if '<status>ok</status>' not in data:
        error('Cannot reboot')
    finally:
      f = self.opener.open('https://%s/data/logout' % self.hostname)
      f.read()
  
  def disconnect(self):
    self._login()
    f = self.opener.open('https://%s/data?get=activeSessions' % self.hostname, '')
    data = f.read()
    doc = xml.dom.minidom.parseString(data)
    for session in doc.getElementsByTagName('session'):
      sessionId = session.getElementsByTagName('sessionId')[0].firstChild.nodeValue
      sessionType = session.getElementsByTagName('sessionType')[0].firstChild.nodeValue
      if sessionType == 'vKVM':
        print 'Disconnecting session %s...' % sessionId
        f = self.opener.open('https://%s/data?set=killSession(%s)' % (self.hostname, sessionId), '')
        f.read()

class Intel(Base):
  FILES = [
    '/Java/release/JViewer.jar',
    '/Java/release/Win32.jar',
    '/Java/release/Win64.jar',
    '/Java/release/Linux_x86_32.jar',
    '/Java/release/Linux_x86_64.jar',
  ]

  def console(self):
    self.check_for_missing_jars()
    opener = urllib2.build_opener()

    session_cookie = self.login(opener)

    f = opener.open('http://%s/rpc/WEBSES/validate.asp' % self.hostname)
    f = opener.open('http://%s/Java/jviewer.jnlp' % self.hostname)
    data = f.read()
    iter = re.finditer(r'<argument>(.*)<', data)
    iter.next()
    iter.next()
    arg3 = iter.next().group(1)
    java('-cp JViewer.jar com.ami.kvm.jviewer.JViewer %s 7578 %s 0 0 0 5120 5123 255 ":Ctrl+Alt+Del:Ctrl Alt Del:Alt+Tab:Alt Tab" EN %s' % (self.hostname, arg3, session_cookie))

  def reboot(self):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPSHandler(context = context), urllib2.HTTPCookieProcessor(cj))

    self.login(opener)

    f = opener.open('https://%s/rpc/hostctl.asp' % self.hostname, 'WEBVAR_POWER_CMD=3&WEBVAR_FORCE_BIOS=0')
    data = f.read()

  def login(self, opener):
    f = urllib2.urlopen('http://%s/rpc/WEBSES/create.asp' % self.hostname, 'WEBVAR_USERNAME=%s&WEBVAR_PASSWORD=%s' % (self.username, self.password))
    data = f.read()
    session_cookie = re.search(r'SESSION_COOKIE\' : \'(.*)\'', data).group(1)
    opener.addheaders.append(('Cookie', 'SessionCookie=%s; Username=%s' % (session_cookie, self.username)))
    return session_cookie

def error(msg = 'Error'):
  print msg
  sys.exit(1)

def select_machine():
  servers = ', '.join([s.name for s in config.servers])
  srv = raw_input('Enter machine (%s): ' % servers)
  if srv in config.servers_dict:
    server = config.servers_dict[srv]
    cls = getattr(sys.modules[__name__], server.type)
    return cls(server.host, server.username, server.password)
  else:
    error()

class Params:
  pass

class Server:
  pass

class Config:
  def __init__(self):
    self.servers = []
    self.servers_dict = {}

def read_config():
  cfg = ConfigParser.RawConfigParser()
  cfg.read(os.path.expanduser('~/.oobcontrol'))
  config = Config()
  for srv in cfg.sections():
    if srv == 'params':
      config.params = Params()
      config.params.java = cfg.get('params', 'java')
    else:
      server = Server()
      server.name = srv
      server.type = cfg.get(srv, 'type')
      server.host = cfg.get(srv, 'host')
      server.username = cfg.get(srv, 'username')
      server.password = cfg.get(srv, 'password')
      config.servers.append(server)
      config.servers_dict[server.name] = server
  return config

def main():
  global config
  config = read_config()

  while True:
    action = raw_input('(c)onsole, (r)eboot, or (d)isconnect ? ')
    action = action.lower()
    if action == 'c':
      select_machine().console()
      break
    elif action == 'r':
      select_machine().reboot()
      break
    elif action == 'd':
      select_machine().disconnect()
      break

if __name__ == '__main__':
  main()
