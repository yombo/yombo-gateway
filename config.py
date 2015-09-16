#!/usr/bin/python
#
# Used to configure the Yombo Gateway. Used for initial configuration and setup as well as
#adjusting settings later.
#
# Details can be found at http://www.yombo.net
"""
Configures and sets up the gateway for use.

On initial setup/configuration, this toold performs the following:
1. Prompts user for username and Gateway setup PIN number.
  The PIN number is setup when the user creates a Gateway using the APi or Yombo App.
2. Interacts with the Yombo API as required to configure the Gateway
3. Setup the GPG/PGP encryption between the gateway and server.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
import signal
import getpass
import sys
import os
import gnupg
import subprocess
import ConfigParser
import gnupg
import requests
import urllib
import json
import getpass
import time
import hashlib
#@TODO: Change later with advanced menu...

apiurl = "https://api.yombo.net"
requests.adapters.DEFAULT_RETRIES = 5

gpg = gnupg.GPG()  #:Build the gpg interface once.
yomboconfig = None
yomboini = ''
account = ''
accounthash = ''
accountsession = ''
apigwdata = None
gwuuid = None
gwpin = None
apikey = 'asdf'

#ensure we are working in the directory where yombo is installed
if os.path.isfile('yombo.tac') == False:
  print "Configuration tool must execute in same folder as Yombo Gateway."
  sys.exit(1)

if os.path.isfile('twistd.pid') == True:
  print "It appears Yombo Gateway is already running.  Cannot run this tool at same time."
  sys.exit(1)

#ensure that usr data directory exists
if not os.path.exists('usr'):
    os.makedirs('usr')
#sql data directory
if not os.path.exists('usr/sql'):
    os.makedirs('usr/sql')
#downloaded modules directory
if not os.path.exists('usr/opt'):
    os.makedirs('usr/opt')
#logging directory
if not os.path.exists('usr/log'):
    os.makedirs('usr/log')

class _Getch:
    """
    Gets a single character from standard input.
    Does not echo to the screen.
    """
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

getch = _Getch()

def signal_handler(signal, frame):
        print 'Quiting at users request.'
        sys.exit(0)

def yomboGetUrl(url):
  """
  Simple wrapper to webGet(), used for calling yombo API.
  """
  global apiurl
  return webGet(apiurl + url)

def webGet(url):
  """
  Makes a web "get" request to a remote server.
  """
  doAgain = True
  while doAgain:
    try:
      r = requests.get(url)
#      print r.text
      return r.json()
    except requests.exceptions.ConnectionError as e:
      print "Error: %s" % e.message
      doContinue = True
      while doContinue:
          print "Try again? y or n"
          command = getch()
          command = command.lower()
          if command == 'y':
            print "\n\rTrying again..."
            doContinue = False
          elif command == 'n':
            sys.exit(1)
          else:
            print "Found: %s" % command

def yomboSend(url, payload, sendType):
  """
  Simple wrapper to webSend(), used for calling yombo API.
  """
  global apiurl
  global accountsession
  headers = {'content-type': "application/json",
             'AUTHORIZATION' : "sessionid %s" % accountsession}
  return webSend(apiurl + url, payload, sendType=sendType, headers=headers)

def webSend(url, payload, **kwargs):
  """
  Used to send data to a remote server.
  """
  headers = kwargs.get('headers', {'content-type': "application/json"})
  sendType = kwargs.get('sendType', 'post').lower()
  doAgain = True
  while doAgain:
    try:
      r = getattr(requests, sendType)(url, data=json.dumps(payload), headers=headers)
#      print r.text
      return r.json()
    except requests.exceptions.ConnectionError as e:
      print "Error: %s" % e.message
      doContinue = True
      while doContinue:
          print "Try again? y or n"
          command = getch()
          command = command.lower()
          if command == 'y':
            print "\n\rTrying again..."
            doContinue = False
          elif command == 'n':
            sys.exit(1)
          else:
            print "Found: %s" % command

def readIni():
    """
    Reads the yombo.ini into global varible yomboconfig (SafeConfigParser).
    """
    global apiurl
    global yomboini
    global yomboconfig
    yomboconfig = ConfigParser.SafeConfigParser()
    try:
        fp = open(yomboini)
        yomboconfig.readfp(fp)
        fp.close()
    except IOError:
        fp.close()
        raise Exception("Error with yombo.ini. Cannot open file. Check permissions or run as user assigned for Yombo Gateway.")
    try:
        environment = yomboconfig.get("server", "environment")
        if environment == "production":
            apiurl = "https://api.yombo.net"
        elif environment == "staging":
            apiurl = "https://apistg.yombo.net"
        if environment == "development":
            apiurl = "https://api.yombo.net"
    except:
        apiurl = "https://api.yombo.net"
        pass

def saveIni():
    """
    Save yomboconfig (SafeConfigParser) to yombo.ini.
    """
    global yomboini
    global yomboconfig
    try:
        setConfig('local','lastsave',str(int(time.time())), False)
        yomboconfig.write(open(yomboini, 'w'))
    except IOError:
        fp.close()
        raise Exception("Error with yombo.ini file, cannot write to file. Have permission?")
    
def deleteIni():
    """
    Delete yombo.ini.
    """
    global yomboini
    global yomboconfig
    if os.path.isfile('yombo.tac') == True:
        os.remove('yombo.ini')

def deleteSql():
    """
    Delete yombo.ini.
    """
    global yomboini
    global yomboconfig
    try:
        if os.path.isfile('usr/sql/config.sqlite3') == True:
            os.remove('usr/sql/config.sqlite3')
    except:
        raise Exception("Error with yombo.ini file, cannot write to file. Have permission?")

def testIni():
    """
    Test to make sure there is a yombo.ini, and find it's location. Then load it's contents.
    """
    global apiurl
    global yomboini
    global gwuuid
    global gwhash
    global yomboconfig
    yomboini = 'yombo.ini'
    if os.path.isfile(yomboini) == False:
        yomboconfig = ConfigParser.SafeConfigParser()
        yomboconfig.add_section('core')
        yomboconfig.add_section('local')
        yomboconfig.add_section('updateinfo')
        gwuuid = None
#        saveIni()
        return False
    else:
        readIni()
        gwuuid = getConfig('core', 'gwuuid')
        return True

def validateIni():
    """
    Simply validates that we have valid values for the gateway yombo.ini file.

    This function is not complete, only checks the hash value.
    """
    global yomboini
    global accountsession
    global gwuuid

    print "Starting validation..."
    readIni()
    gwuuid = getConfig('core', 'gwuuid')

    response = yomboGetUrl("/api/v1/gateway_registered/%s?sessionid=%s" % (gwuuid, accountsession))
    print("Checking gateway authentication hash..."),
    if response['gwhash'] != getConfig('core', 'gwuuid'):
        print "Invalid...Fixed."
        setConfig('core', 'gwuuid', response['gwhash'])
    else:
        print "Good."
       
    saveIni()

def getConfig(cfgSection, cfgKey):
    """
    Fetches a value from the configuration file.
    """
    global yomboconfig

    if yomboconfig.has_option(cfgSection, cfgKey):
      value = yomboconfig.get(cfgSection, cfgKey)
      try:
        return int(value)
      except:
        try:
          return float(value)
        except:
          return value
    else:
      return None

def setConfig(cfgSection, cfgKey, cfgValue, saveIt=True):
    """
    Save the key information into the yombo.ini file.

    When called, updates yomboconfig with the new setting.  Also, calls saveIni().
    """
    global yomboconfig

    if getConfig(cfgSection, cfgKey) == cfgValue:
        return True

    if not yomboconfig.has_section(cfgSection):
       yomboconfig.add_section(cfgSection)
    yomboconfig.set(cfgSection, cfgKey, str(cfgValue))
    
    if cfgSection != 'local':    
      if not yomboconfig.has_section('updateinfo'):
        yomboconfig.add_section('updateinfo')

      updateItem = cfgSection + "_+_" + cfgKey + "_+_time"
      yomboconfig.set('updateinfo', updateItem, str( int( time.time() ) ) )
      updateItem = cfgSection + "_+_" + cfgKey + "_+_hash"
      yomboconfig.set('updateinfo', updateItem, hashlib.sha224(str(cfgValue)).hexdigest() )

    if saveIt == True:
        saveIni()
    return True

def deleteConfig(cfgSection, cfgKey):
    """
    Removes a configuration items. Calls saveIni().
    """
    global yomboconfig

    if yomboconfig.has_section(cfgSection):
      if yomboconfig.has_option(cfgSection, cfgKey):
        yomboconfig.remove_option(cfgSection, cfgKey)
    saveIni()
    return True

def setupBundle(**kwargs):
  """
  Bundle stores all the information relating to a gateway and it's save meta state.
  """
  bundle = { 
  'both': {
      'core' : {
        'gwuuid' : '',
        'gwhash' : '',
        'gpgkeyid' : '',
        'gpgkeyascii' : '',
        'label' : '',
        'description' : '',
      },
      'location' : {
        'latitude' : 0.0,
        'longitude' : 0.0,
        'elevation' : 0,
      },
      'listner' : {
        'port' : '8443',
      },
      'server' : {
        'environment' : 'production',
      },
  },
  'remote': {
  },
  'local': {
      'local' : {
      },
      'updateinfo' : {
      },
  },
  'meta':{
      'dirtyIni':False,
      'dirtyApi':False,
  },
  }
  return bundle

def updateBundle(bundle, location, section, item, value, setmeta=True):
  """
  Update a key (item) of the bundle.  Sets it's dirty status to true.
  """
  if location not in bundle:
      bundle[location] = {}
  if section not in bundle[location]:
      bundle[location][section] = {}
  bundle[location][section][item] = value
  if setmeta == True:
    bundle['meta']['dirtyIni'] = True
    bundle['meta']['dirtyApi'] = True

def loadBundleFromFile(bundle=None):
  global gwuuid
  global yomboconfig

  readIni()

  gwuuid = getConfig('core', 'gwuuid')
  if bundle == None:
    bundle = setupBundle()

  for section in yomboconfig.sections():
      for item in yomboconfig.options(section):
          if section == 'updateinfo':
              continue
          location = 'both' if section != 'local' else 'local'
          updateBundle(bundle, location, section, item, getConfig(section, item), False)
  return bundle

def updateBundleFromAPI(gwuuid, bundle=None):
  bundle = setupBundle() if bundle == None else bundle
  response = gatewayFetchDetail(gwuuid)
  variables = response['variables']

  bundle['both']['core']['gwuuid'] = response['gwuuid']
  bundle['both']['core']['gwhash'] = response['gwhash']
  bundle['both']['core']['gpgkeyid'] = response['gpgkeyid']
  bundle['both']['core']['gpgkeyascii'] = response['gpgkeyascii']
  bundle['both']['core']['label'] = response['label']
  bundle['both']['core']['description'] = response['description']

  for location in variables:
      for item in variables[location]:
          if location != 'core':
              updateBundle(bundle, 'both', location, item, variables[location][item])

  bundle['meta']['dirtyIni'] = True
  return bundle

def saveBundleToIni(bundle):
  for dest in bundle:
    if dest != 'meta':
      for location in bundle[dest]:
          for item in bundle[dest][location]:
              if dest in ('both','local'):
                setConfig(location, item, bundle[dest][location][item], False)
  saveIni()
  bundle['meta']['dirtyIni'] = False
  
def saveBundleToAPI(bundle, newgw=False):
#  allowedInCore = ['gwuuid', 'gwhash', 'gpgkeyid', 'gpgkeyascii', 'label', 'description']
  variables = {}
  for dest in bundle:
      if dest in ('both','remote'):
        for location in bundle[dest]:
            for item in bundle[dest][location]:
                if location != 'core':
                    if location not in variables:
                        variables[location] = {}
                    variables[location][item]=bundle[dest][location][item]
  
  upload = {
        'gpgkeyid' : bundle['both']['core']['gpgkeyid'],
        'gpgkeyascii' : bundle['both']['core']['gpgkeyascii'],
        'label' : bundle['both']['core']['label'],
        'description' : bundle['both']['core']['description'],
        'variables' : variables,
      }

  if newgw == False:
#    print "in savebundletoapi - posting update!"
#    print("/api/v1/gateway_registered/%s :: %s :: %s" % (gwuuid, upload, 'patch'))
    yomboSend("/api/v1/gateway_registered/%s" % gwuuid, upload, 'patch')
  else:
#    print "in savebundletoapi - posting new!"
#    print("/api/v1/gateway_registered :: %s " % (upload,))
    results = yomboSend("/api/v1/gateway_registered", upload, 'post')

    updateBundleFromAPI(results['gwuuid'], bundle)
  
  bundle['meta']['dirtyApi'] = False    

def gatewayFetchDetail(gwuuid):
      global accountsession
      return yomboGetUrl("/api/v1/gateway_registered/%s?sessionid=%s" % (gwuuid, accountsession))

def gatewayFetchList():
      global accountsession
      global apigwdata
      response = yomboGetUrl("/api/v1/gateway_registered?sessionid=%s" % (accountsession,))
      if 'objects' in response:
        apigwdata = {}
        for (i, item) in enumerate(response['objects']):
          apigwdata[item['gwuuid']] = item
      else:
        print "Error with session: %s" % response['errormessage']
        raise Exception("Error fetching gateway list.")
    
def GPGKeyGenerate(**kwargs):
    """
    Generates a new GPG key pair.  Updates yombo.ini and calls sendKey() when done.
    """
    global gwuuid
    global yomboconfig

    key = ''
    try:
        key = getConfig('core', 'gpgkeyid')
    except ConfigParser.NoSectionError:
        raise Exception("Error with yombo.ini. !!!!")
    except ConfigParser.NoOptionError:
        key = ''
    except Exception,e :
        print e
        return

    if key != '':
        global getch
        print "A GPG keypair already exists, or at least Yombo Gateway software says it does.\n\r"
        doContinue = True
        while doContinue:
          print "Do you want to force a new one to be generated? (y/n/?): "
          command = getch()
          command = command.lower()
          if command == 'y':
            doContinue = False
          elif command == 'n':
            return
          elif command == '?':
            print "Selecting yes (y) will generate a new key pair and assign this key to be used with the currently configured gateway."
            print "Selecting no (n) will return to previous menu."

    print "Generating 2048 bit RSA key pair. GPG can take a while (several minutes).\n\rUse your mouse and keyboard to generate random data.\n\r"
    print "Surf the web, listen to some music, sit back and relax.\n\r"
    global gpg

    input_data = gpg.gen_key_input(
        name_email=gwuuid + "@yombo.me",
        name_real="Yombo Gateway",
        name_comment=gwuuid,
        key_length=2048)

    newkey = gpg.gen_key(input_data)
#    print "\n\rGenerated key: '%s'\n\r" % newkey

    if newkey == '':
        print "\n\rERROR: Unable to generate GPG keys.... Is GPG installed and configured? Is it in your path?\n\r"
        myExit()

    private_keys = gpg.list_keys(True)
    keyid = ''

    for key in private_keys:
        if str(key['fingerprint']) == str(newkey):
            keyid=key['keyid']
    asciiArmoredPublicKey = gpg.export_keys(keyid)
    updateBundle(bundle, 'both', 'core', 'gpgkeyid', keyid)
    updateBundle(bundle, 'both', 'core', 'gpgkeyascii', asciiArmoredPublicKey)
    sendKey(keyid, asciiArmoredPublicKey)
    print "New keys (public and private) have been saved to key ring."
        
def GPGKeySelect(bundle):
    """
    Provides a simple method for selecting a key to use. Updates
    yombo.ini and calls sendKey() to make sure keys.yombo.net has it.
    """
    global getch
    global gpg

    existingKey = bundle['both']['core']['gpgkeyid']
    public_keys = gpg.list_keys()
    private_keys = gpg.list_keys(True)

    pubkeys = {}
    privkeys = {}

    for key1 in public_keys:
        pubkeys[key1['keyid']] = key1

    for key2 in private_keys:
        privkeys[key2['keyid']] = key2

    validpairs = ['none']
    doContinue = True
    while doContinue:
      print "\n\r\n\rSelect a key to use for: %s" % bundle['both']['core']['label']
      print "========================"
      c = 0
      for key in privkeys:
        c += 1
        if key in pubkeys:
            uids = ''
            for uid in privkeys[key]['uids']:
                if uids != '':
                    uids += ", "
                uids = uid
            validpairs.append(privkeys[key])
            selectedPair = ''
            if privkeys[key]['keyid'][-8:] == existingKey[-8:]:
                selectedPair = " (selected)"
            print "%2s) %s <keyid:%s>%s" % (c, uids, privkeys[key]['keyid'][-8:],selectedPair)

      print " N) Generate a new key"
      print " H) Help"
      print " E) Exit to previous menu"
      print " Q) Quit"
      pair = raw_input("Select a keypair: ")
      if pair.lower() == 'e':
        return
      elif pair.lower() == 'h':
        print "\n\rGPG (or PGP) keys are used for many reasons. The primary reason is to encrypt sensitive information"
        print "or commands.  For example, when passwords are stored outside of the local gateway, they will be"
        print "encrypted with the 'public' key. This means only the private key which is only sotred on the local"
        print "gateway can be used to decrypt this information.  Also, remote services and applications can"
        print "encrypt data and commands sent to the gateway so that only the gateway knows what is supposed to"
        print "take place.\n\rCAUTION: The strenght of GPG/PGP keys is only as good as it's private key. Don't"
        print "ever give out the private key, no ONE - not even those helping to troubleshoot a problem.!"
        print "\n\rFrom this menu, you can generate a new key (n) or select an existing keypair to use."
      elif pair.lower() == 'q':
        myExit()
      elif pair.lower() == 'n':
        result = GPGKeyGenerate()
        if isinstance(result, dict) and len(result) == 2:
            return result
        else:
            print "\n\rError with key generation."
      try:
        pair = int(pair)
      except ValueError:
        print "\n\rInvalid keypair.  Try again."
        continue
      try:
        #seperated out incase there is an error
        keyid = validpairs[pair]['keyid']
        asciiArmoredPublicKey = gpg.export_keys(keyid)
        updateBundle(bundle, 'both', 'core', 'gpgkeyid', keyid)
        updateBundle(bundle, 'both', 'core', 'gpgkeyascii', asciiArmoredPublicKey)
        return
      except IndexError:
        print "\n\rInvalid keypair.  Try again."


def sendKey(keyid, asciiArmoredPublicKey):
    """
    Sends your *public* key to keys.yombo.net.  This permits other
    services and gateways to send encrypted commands to this gateway.
    """
    cmd = ['gpg', '--send-keys', '--keyserver', 'keys.yombo.net', keyid]
    result = subprocess.check_call(cmd)
#    if result == 0:
#        print "\n\rPublic GPG/PGP key sent to keys.yombo.net. \n\r\n\r"


def menuStart(**kwargs):
  preselect = '' if 'preslect' not in kwargs else kwargs['preselect']

  global getch
  global gwuuid
  global apigwdata
  
  gatewayFetchList()
  gwlabel = ''
  bundle = ''
  if gwuuid != None:
    if gwuuid not in apigwdata:
      print "\n\rError: Invalid configuration file. Create a new gateway or Assign (download) and existing gateway."
      gwuuid = None
    else:
      gwlabel = apigwdata[gwuuid]['label']
  else:
      gwlabel = "*None*"

  while True:
    command = ""
    if preselect == "":
      if gwuuid != None:
        if gwuuid not in apigwdata:
          print "\n\rError: Invalid configuration file. Create a new gateway or Assign (download) and existing gateway."
          gwuuid = None
        else:
          gwlabel = apigwdata[gwuuid]['label']
      else:
          gwlabel = "*None*"

      print ""
      print "Main Menu"
      print "========="
      print "Select a function"
      print "N) ** Create a new gateway and configure it"
      if gwuuid != None:
        print "C) Configure current gateway: % s" % gwlabel
      print "A) ** Assign an existing gateway to this machine"
      print "P) ** Purge gateway database and yombo.ini configurations"
      print "    ** = This deletes any local configurations and device history."
      print "Q) Quit"
      print "Enter a command: ",
      command = getch()
      print ""
      command = command.lower()
    else:
      command == preselect.lower()
      preselect = ""
    if command == 'n':
#      try:
        bundle = gatewayNew()
        gwuuid = bundle['both']['core']['gwuuid']      
#      except Exception, e:
#        print e
    elif command == 'c' and gwuuid != None:
      menuGateway()
    elif command == 'a':
      try:
        bundle = gatewaySelectExisting()
        gwuuid = bundle['both']['core']['gwuuid']      
        saveBundleToIni(bundle) 
      except Exception, e:
        print e
    elif command == 'p':
      menuDoesntExist()
    elif command == 'q':
      myExit()
    else:
      print "Invalid command.  Try again.\n\r"

def menuDoesntExist():
  print "This menu hasn't been defined.  Returning to previous menu."
  return

def gatewaySelectExisting():
    global accountsession
    global apigwdata
    global gwuuid

    print "\n\rSelect existing gateway menu"
    print "============================"
    validgws = {}
    doContinue = True
    while doContinue:
      c = 0
      for item in apigwdata:
        c += 1
        validgws[c] = apigwdata[item]['gwuuid']
        print "%2s) %s (%s)" % (c, apigwdata[item]['label'], apigwdata[item]['gwuuid'][:10])
      print " E) Exit to previous menu"
      input = raw_input("Select a gateway: ")
      if input.lower() == 'e':
        return
      try:
         input = int(input)
      except ValueError:
        print "\n\rInvalid gateway selected.  Try again."
        continue
      if input not in validgws:
        print "\n\rInvalid gateway selected.  Try again."
        continue
      try:
        gwuuid = validgws[input]
        print "\n\rGateway Selected : %s" % (apigwdata[gwuuid]['label'])
        bundle = updateBundleFromAPI(gwuuid)
        saveBundleToIni(bundle)
        doContinue = False
      except IndexError:
        print "\n\rInvalid gateway selected. Try again."

    global gpg
    existingKey = bundle['both']['core']['gpgkeyid']
    public_keys = gpg.list_keys()
    private_keys = gpg.list_keys(True)

    pubkeys = {}
    privkeys = {}

    for key1 in public_keys:
        pubkeys[key1['keyid']] = key1

    for key2 in private_keys:
        privkeys[key2['keyid']] = key2

    validpairs = ['none']
    localKeyFound = False

    for key in privkeys:
        c += 1
        if key in pubkeys:
            uids = ''
            for uid in privkeys[key]['uids']:
                if uids != '':
                    uids += ", "
                uids = uid
            validpairs.append(privkeys[key])
            if privkeys[key]['keyid'][-8:] == existingKey[-8:]:
                localKeyFound = True

    if localKeyFound == False:
        print "\n\rReceived a GPG / PGP key id that was not found in your keyring."
        print "Select an existing key or generate a new key for this gateway."
        print "**OR** copy the existing key to this computer and re-run this tool."
        if GPGKeySelect(bundle) == False:
            raise Exception("Problem with encryption key pair selection")
#        updateBundle(bundle, 'both', 'core', 'gpgkeyid', results['gpgkeyid'])
#        updateBundle(bundle, 'both', 'core', 'gpgkeyascii', results['gpgkeyascii'])

    if localKeyFound == False:
        sendKey(results['gpgkeyid'], results['gpgkeyascii'])
    else:
        print "Key reported from server was found on this computer. Great!"
    print "Gateway configuration downloaded and saved."
    return bundle

def menuGateway(**kwargs):
  preselect = '' if 'preslect' not in kwargs else kwargs['preselect']

  global getch
  global gwuuid
  global apigwdata
  global bundle

  if gwuuid != None:
    if gwuuid not in apigwdata:
      print "\n\rError: Invalid configuration file. Create a new gateway or Assign (download) and existing gateway."
      gwuuid = None
    else:
      bundle = loadBundleFromFile()
      gwlabel = bundle['both']['core']['label']
  else:
      print "\n\rNo current gateway found. Returning to main menu."
      return

  while True:
    command = ""
    if preselect == "":
      print "\n\r\n\rGateway Settings Menu"
      print "========================="
      print "- - Gateway Settings : %s" % gwlabel
      print "C) Change Label & Description"
      print "B) Basic Configuration"
      print "L) Change Location"
      print "M) Manage keys"
      print "V) Validate configuration"
      print "D) Delete local configuration & device history and refresh from online"
      print "- - Navigation - -"
      print "A) Accept and Save changes"
      print "E) Exit to previous menu"
      print "Q) Quit"
      print "Enter a command: ",
      command = getch()
      print ""
      command = command.lower()
    else:
      command == preselect.lower()
      preselect = ""
    if command == 'm':
      GPGKeySelect(bundle)
    elif command == 'c':
      gatewayLabel(bundle)
      gwlabel = bundle['both']['core']['label']
    elif command == 'b':
      gatewayBasic(bundle)
    elif command == 'v':
      validateIni()
    elif command == 'd':
      deleteIni() + "&format=json"
      deleteSql()
      bundle = updateBundleFromAPI(gwuuid)
      gwlabel = bundle['both']['core']['label']
      saveBundleToIni(bundle)      
    elif command == 'l':
      gatewayLocation(bundle)
    elif command == 'a':
      saveBundleToIni(bundle) 
      saveBundleToAPI(bundle) 
    elif command == 'e':
      checkIfDirty(bundle)
      return bundle
    elif command == 'q':
      checkIfDirty(bundle)
      myExit()
    else:
      print "Invalid command.  Try again.\n\r"

def checkIfDirty(bundle):
    if bundle['meta']['dirtyApi'] == True or bundle['meta']['dirtyIni'] == True:
        print "Changes haven't been saved. Changes will be lost if not saved."
        doContinue = True
        while doContinue:
          print "Save now? (y/n): "
          command = getch()
          command = command.lower()
          if command == 'y':
            saveBundleToIni(bundle) 
            saveBundleToAPI(bundle) 
            gatewayFetchList()
            return
          elif command == 'n':
            return
      
def gatewayNew():
  global bundle
  global getch
  global accountsession

  print "\n\rCreating a new gateway.\n\rThis will delete any existing gateway configured."
  doContinue = True
  while doContinue:
    print "Continue? (y/n): "
    command = getch()
    command = command.lower()
    if command == 'y':
      doContinue = False
    elif command == 'n':
      raise Exception("New gateway config canceled!")

  bundle = setupBundle()
  updateBundle(bundle, 'both', 'backup', 'devicehistory', 1)
  
  if gatewayLabel(bundle) == False:
      print "Error collecting basic information, not creating new gateway."
      return
  
  if gatewayLocation(bundle) == False:
      print "Error collecting location and timezone information, not creating new gateway."
      return

  if GPGKeySelect(bundle) == False:
      print "Error with encryption keys, not creating new gateway."
      return

  print "\n\rDone. Saving locally and saved to Yombo servers."
  deleteIni()
  deleteSql()
  saveBundleToIni(bundle) 
  saveBundleToAPI(bundle, True)
  gatewayFetchList()
  return bundle

def gatewayLabel(bundle):
  doContinue = True
  doSkip = False
  label = bundle['both']['core']['label']
  desc = bundle['both']['core']['description']
  newLabel = ''
  newDesc = ''
  while doContinu + "&format=json"e:
    if doSkip == False:
      print "\n\rBasic gateway information."
      newLabel = raw_input('Gateway label [%s]: ' % (newLabel if newLabel != '' else label,))
      showDesc = newDesc[0:20] if newDesc != '' else desc[0:20]
      if len(showDesc) == 20:
          showDesc = showDesc + "..."
      print "Gateway description [%s]" % showDesc
      newDesc = raw_input('--> ')
      if len(newLabel) == 0:
          if len(label) == 0:
              print "You must enter a gateway label."
              continue
          else:
              label = newLabel
      else:
          label = newLabel

      if len(newDesc) > 0:
          desc = newDesc
              
    doSkip = False
    print "Accept / Edit / Quit  (a/e/q/?):"
    command = getch()
    command = command.lower()
    if command == 'a':
      updateBundle(bundle, 'both', 'core', 'label', label)
      updateBundle(bundle, 'both', 'core', 'description', desc)
      return True
    elif command == 'e':
      continue
    elif command == 'q':
      return False
    elif command == '?':
      print "Selecting yes (y) will accept the label and decription and continue. Selecting no (e)"
      print "will prompt for these items again. To quit, select q."
      doSkip = True
    else:
      doSkip = True
      continue

def gatewayBasic(bundle):
  yesno = {1:'yes',0:'no'}
  
  doContinue = True

  while doContinue:
    print "\n\rMisc settings"
    print "============="
    print "H) Send device state history to yombo for achival. Current: (%s)" % yesno[ bundle['both']['backup']['devicehistory'] ]
    print "   Allows you to view historical data and trending online (future feature)."
    print "- - - - - - - - - - - - - "
    print "E) Done"

    command = getch()
    command = command.lower()
    if command == 'h':
#      print "toggle history....%d" % bundle['both']['backup']['devicehistory']
      newval = 0 if bundle['both']['backup']['devicehistory'] == 1 else 1
      updateBundle(bundle, 'both', 'backup', 'devicehistory', newval)
#      print "toggle history....%d" % bundle['both']['backup']['devicehistory']

    elif command == 'e':
      return

def gatewayLocation(bundle):
  print "\n\r\n\r========================="
  print "Set location and timezone"
  print "========================="
  print "Fetching information based on IP address..."
  result = yomboGetUrl("/api/v1/location?sessionid=%s" % (accountsession,))
  r = result['objects'][0]
  latitude = r['latitude']
  longitude = r['longitude']
  timezone = r['time_zone']
  locationName = "%s, %s, %s (unsaved, reference only)" % (r['city'], r['region_name'], r['country_code3'])
  elevation = 2400

  doContinue = True
  while doContinue:

    print "\n\r\n\rSelect action"
    print "====================="
    print "G) Use google maps address search tool"
    print "I) Use my IP address for an approximation\n\r"
    print "   (Enter item number to edit)"
    print "1) Location: %s" % locationName
    print "2) Time Zone: %s" % timezone
    print "3) Latitude: %.6f" % latitude
    print "4) Longitude: %.6f" % longitude
    print "5) Elevation: %d\n\r" % elevation
    print "A) *** Accept current values ***"
    print "H) Help or details about these choices"
    print "E) Exit to previous menu (information may be lost)"
    print "Q) Quit"
    command = getch()
    command = command.lower()
    
    if command == 'i' or command == 'g':
      if command == 'i':
        print "\n\rFetching location information based on your IP address."
        result = yomboGetUrl("/api/v1/location?sessionid=%s" % (accountsession,))
        r = result['objects'][0]
        latitude = r['latitude']
        longitude = r['longitude']
        timezone = r['time_zone']
        elevation = 2400
        locationName = "%s, %s, %s (unsaved, reference only)" % (r['city'], r['region_name'], r['country_code3'])
      else:
        print "\n\rEnter a search location. As vague or detailed as desired. Examples: San Francisco, CA"
        print "60622  (zip code search);  123 Main Street, Somecity"
        getLocation = raw_input("Google Search:")
        print "\n\rChatting with google..."
        query = urllib.urlencode({'address':getLocation, 'sensor':'false'})
        result = webGet("https://maps.googleapis.com/maps/api/geocode/json?%s" % query)
        if result['status'] == 'OK':
          r = result['results'][0]
          latitude = r['geometry']['location']['lat']
          longitude = r['geometry']['location']['lng']
          locationName = r['formatted_address']

          query = urllib.urlencode({'locations':'%f,%f' % (latitude, longitude), 'sensor':'false'})
          result = webGet("https://maps.googleapis.com/maps/api/elevation/json?%s" % query)
          if result['status'] == 'OK':
            elevation = int(result['results'][0]['elevation'])
          else:
            elevation = 2400

          query = urllib.urlencode({'location':'%f,%f' % (latitude, longitude), 'timestamp': int(time.time()), 'sensor':'false'})
          result = webGet("https://maps.googleapis.com/maps/api/timezone/json?%s" % query)
          if result['status'] != 'INVALID_REQUEST':
            timezone = result['timeZoneId']
          else:
#            print result
            print "Error getting timezone from google!"
            timezone = raw_input("Visit https://en.wikipedia.org/wiki/List_of_tz_database_time_zones and enter a timezone:")

    elif command == 'g':
      return
    elif command == 'h':
      print "\n\rThis menu configures the gateway location and timezone. Information is used to"
      print "calculate sunrise, sunset, if it's dark/light outside, moonrise/moonset, and other"
      print "time and location based events.  This information is not shared and only used by the"
      print "to make these calculations. However, this data is sent to Yombo so that the gateway"
      print "configuration can be downloaded if needed. Only timezone, latitude, longitude, and"
      print "are stored."
      print "\n\rThe timezone should be accurate, however, the latitude, longitude, and elevation"
      print "only need to be approximate.  Greater accuracy does provide greater accuracy on various"
      print "calculations."
      print "\n\rIP address information can be incorrect, but it's a quick method to set location."
      print "\n\rGoogle results can provide better resolution and includes better elevation information."
      print "When using google, as must or little address information can be used. Such as, just"
      print "the entering a state may be enough, otherwise, you can enter your street name (with"
      print "or without house number) and city, state will produce better results."
      print "\n\r*Google api is called directly though this configuration tool when using Google."

    elif command == 'a':
      updateBundle(bundle, 'both', 'location', 'latitude', latitude)
      updateBundle(bundle, 'both', 'location', 'longitude', longitude)
      updateBundle(bundle, 'both', 'location', 'timezone', timezone)
      updateBundle(bundle, 'both', 'location', 'elevation', elevation)
      doContinue = False
    elif command == 'e':
      return False
    elif command == 'q':
      myExit()

def myExit():
  print "Good bye...\n\r"
  sys.exit()

def checkLoginCredentials():
    global account
    global accounthash
    global accountsession
    global apikey
    account = getConfig('local','account')
    accounthash = getConfig('local','accounthash')
    accountsession = getConfig('local','accountsession')

    if account == None:
      return False
    if accountsession != None:
      response = yomboGetUrl("/api/v1/user_validatesession?sessionid=%s" % (accountsession,))
      if response['result'] == 'success':
        print "Valid account found at Yombo."
        deleteConfig('local','accounthash')
        return True
      else:
        return False
    if accounthash != None:
      response = yomboGetUrl("/api/v1/user_loginwithhash?apikey=%s&username=%s&userhash=%s" % (apikey, account, accounthash))
      if response['result'] == 'success':
        print "User has a valid userhash. Saving session id, clearing userhash."
        setConfig('local','accountsession', response['sessionid'])
        deleteConfig('local','accounthash')
        return True
      else:
        return False
    return False

def promptForString(promptDescription, promptLine, showInput=True, required=True):
    print "\n%s\n" % promptDescription
    while doPrompt:
      doAsk = True
      while doAsk:
        if showInput:
            theinput = raw_input("%s:" % promptLine)
        else:
            theinput = getpass.getpass("%s:" % promptLine)
        if len(theinput) == 0 and required == False:
          doAsk = False
          return theinput
        else:
          print "\n\nThis value is required.\n"


def promptLoginCredentials():
    global account
    global accountsession
    account = getConfig('local','account')
    if checkLoginCredentials():
      return

    doPrompt = True

    print "In order to configure this gateway, we need your credentials to connect to Yombo servers."
    while doPrompt:
      doAsk = True
      while doAsk:
        theinput = raw_input("Enter username [%s] :" % account)
        if len(theinput) == 0:
          theinput = account
        if theinput.isalnum():
          doAsk = False
          account = theinput
        else:
          print "The account username must be alphanumeric."

      doAsk = True
      accountpassword = ''
      while doAsk:
        theinput = getpass.getpass("Enter password:")
        if len(theinput) >= 4:
          doAsk = False
          accountpassword = theinput
        else:
	  print "The password must be at least 4 characters."

      response = yomboGetUrl("/api/v1/user_loginwithpassword?apikey=asdf&username=%s&password=%s" % (account, accountpassword))
      if response['result'] == 'success':
        print "\n\rValid credentails found at Yombo."
        setConfig('local','account', account)
        setConfig('local','accountsession', response['sessionid'])
        accountsession = response['sessionid']
        doPrompt = False
      else:
        print "\n\rYombo reports problem with credentials: %s\n\r" % response['errormessage']


# Flow:
# Check if already configured.
# If new:
#  Prompt for gateway setup PIN.  This is required to setup gateway, no other method will work going forward.
#  Configure gateway - setup yombo.ini file, SQL file, GPG keys.

# If not new:
#   Check if gwuuid and gwhash is valid against API.
#   If valid, prompt user asking what they want to do (wipe, change settings, manage GPG keys)
#
#   If not valid:
#     Ask user: Delete all configrations, start over.
#       This will reqire user to use mobile app or website to request gateway pin setup.


if testIni() == False:  # a new gateway setup
    print "\n\rIt appears this is a new gateway installation or the configuration has been wipped.\n\r"
    print "You will need the one-time Gateway setup PIN code. This is provided when a new Gateway is\n\r"
    print "created. This PIN code is good for only one use. If you new a new PIN, use the Yombo APP and\n\r"
    print "select the gateway you wish to setup. Go into the Gateway configurations and select\n\r"
    print "'Request setup PIN code.\n\r"

    configMode = "PINSetup"

    doPrompt = True
    while doPrompt:
        gatewayPIN = promptForString("", "Gateway PIN Code")
        response = yomboGetUrl("/api/v1/gateway!setupPin?apikey=%s&pincode=%s" % (apikey, gatewayPIN) )
      if response['result'] == 'Success':
        print "\n\rValid gateway PIN code found. Configuring gateway."
        setConfig('core','gwuuid', response['Response']['Gateway']['gwuuid'])
        setConfig('core','gwhash', response['Response']['Gateway']['gwhash'])
        doPrompt = False
      else:
        print "\n\rYombo reports problem with gateway PIN Code.\n\r"


    # setup GPG keys now.

else:
    menuStart()








