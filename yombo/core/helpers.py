#This file was created by Yombo for use with Yombo Gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Various helper functions to 'get stuff done'. These range from simple
function wrappers to larger functions.  Look here first for a function that
may do what you need. Next, look for a library that may contain what you
need.  If you still can't find the function you are looking for look through
http://projects.yombo.net/projects/gateway to see if a feature request or
issue has been submitted for it. You can also just create it and contribute
the code.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""
import gnupg
import random
import string
import re    
from subprocess import Popen, PIPE, STDOUT

from twisted.internet import defer, reactor

from yombo.core.db import get_dbtools
from yombo.core.log import getLogger
from yombo.core.exceptions import GWException, NoSuchLoadedComponentError

logger = getLogger('core.helpers')

yomboconfigs = None
yombodbtools = None

def sleep(secs):
    """
    A simple non-blocking sleep function.  This generates a twisted  
    deferred. You have to decorate your function to make the yield work  
    properly.  

    **Usage**:

    .. code-block:: python

       from twisted.internet import defer
       from yombo.core.helpers import sleep

       @defer.inlineCallbacks
       def myFunction(self):
           logger.info("About to sleep.")
           yield sleep(5.4) # sleep 5.4 seconds.
           logger.info("I'm refreshed.")

    :param secs: Number of seconds (whole or partial) to sleep for.
    :type secs: int of float
    """
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d

def generateRandom(**kwargs):
    """
    Generate a random alphanumeric string. *All arguments are kwargs*.
    
    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import generateRandom
       someRandonness = generateRandom(letters="abcdef0123456") #make a hex value
    
    :param length: Length of the output string. Default: 32
    :type length: int
    :param letters: A string of characters to to create the new string from.
        Default: letters upper and lower, numbers 0-9
    :type letters: string
    :return: A random string that contains choices from `letters`.
    :rtype: string
    """
    length = kwargs.get('length', 32)
    letters = kwargs.get('letters', None)

    if not hasattr(generateRandom, 'randomStuff'):
        generateRandom.randomStuff = random.SystemRandom()

    if letters == None:
        lst = [generateRandom.randomStuff.choice(string.ascii_letters + string.digits) for n in xrange(length)]
        return "".join(lst)
    else:
        lst = [generateRandom.randomStuff.choice(letters) for n in xrange(length)]
        return "".join(lst)

def generateUUID(**kwargs):
    """
    Create a 30 character UUID, where only 26 of the characters are random.
    The remaining 4 characters are used by developers to track where a
    UUID originated from.  

    **All arguments are kwargs.**

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import generateUUID
       newUUID = generateUUID(maintype='G', subtype='a2A')

    :param maintype: A single alphanumeric (0-9, a-z, A-Z) to note the uuid main type.
    :type maintype: char
    :param maintype: Up to 3 characters (0-9, a-z, A-Z) to note the uuid sub type.
    :type subtype: string
    :return: A random string, with source identifiers at the end, 30 bytes in length.
    :rtype: string
    """
    uuid = generateRandom(length=26)
    maintype= kwargs.get('maintype', 'z')
    subtype= kwargs.get('subtype', 'zzz')

    okPattern = re.compile(r'([0-9a-zA-Z]+)')

    m = re.search(okPattern, maintype)
    if m:
        pass
    else:
        maintype = "z"
        subtype = "zzz"

    m = re.search(okPattern, subtype)
    if m:
        pass
    else:
        subtype = "zzz"

    if len(maintype) != 1:
        type = "z";

    if len(subtype) == 1:
        subtype = "zz" + subtype
    elif len(subtype) == 2:
        subtype = "z" + subtype
    elif len(subtype) == 3:
        pass
    else:
        subtype = "zzz"

    tempit = uuid + subtype + maintype
    return tempit

def getConfigTime(section, key):
    """
    Get the time the configuration was last updated.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getConfigTime
       secondSinceEpoch = getConfigTime("core", "gwuuid")

    :param section: The section of the configuration to load. IE: core, etc.
    :type section: string
    :param key: The configuration key. It's the entry under a section.
    :type key: string
    """
    global yomboconfigs
    if yomboconfigs == None:
        yomboconfigs = getComponent('yombo.gateway.lib.configuration')
    return yomboconfigs.getConfigTime(section, key)

def getConfigValue(section, key, default=None):
    """
    Get a configuration value. These were the initial configurations loaded
    in from yombo.ini and stored in a cache + sqlite DB at startup.

    The section and key are **case insensitive** and all sections and keys
    will be converted to lowercase.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getConfigValue
       gatewayUUID = getConfigValue("core", "gwuuid", None)

    :param section: The section of the configuration to load. IE: core, etc.
    :type section: string
    :param key: The configuration key. It's the entry under a section.
    :type key: string
    :param default: If no value is found for the given section/key, then this value will be returned.
    :type default: string or int
    :return: Requested configuration param.
    :rtype: string, int, default, or None
    """
    global yomboconfigs
    if yomboconfigs == None:
        yomboconfigs = getComponent('yombo.gateway.lib.configuration')
    return yomboconfigs.read(section, key, default)

def setConfigValue(section, key, value):
    """
    Set a configuration value.

    The section and key are **case insensitive** and all sections and keys
    will be converted to lowercase.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import setConfigValue
       getConfigValue("newsection", "newkey", "theNewvalue")

    :param section: The section of the configuration to save to. IE: core, etc.
    :type section: string
    :param key: The configuration key. It's the entry under a section.
    :type key: string
    :param value: If no value is found for the given section/key, then this value will be returned.
    :type value: string or int
    """
    global yomboconfigs
    if yomboconfigs == None:
        yomboconfigs = getComponent('yombo.lib.Configuration')
    return yomboconfigs.write(section, key, value)

def getComponent(name):
    """
    Return loaded component (module or library). This can be used to find
    other modules or libraries. The getComponent uses the Fuzzysearch_
    class to make searching easier, but can only be off one or two letters
    due to importance of selecting the correct library or module.

    All component names are stored in lower case, the search will convert
    requests to lower case.    

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getComponent
       someOtherModule = getComponent("Yombo.Gateway.module.someOtherModule")
       someOtherModule.setDisplay("Hello world.") # this module would set the
                                                  # display and send a device
                                                  # status message
        
    :raises NoSuchLoadedComponentError: When the requested component cannot be found.
    :param name: The name of the component (library or module) to find.  Returns a
        pointer to the object so it's functions and attributes can be accessed.
    :type name: string
    :return: Pointer to requested library or module.
    :rtype: Object reference
    """
    if not hasattr(getComponent, 'components'):
        from yombo.lib.loader import getTheLoadedComponents
        getComponent.components = getTheLoadedComponents()
    try:
        return getComponent.components[name.lower()]
    except KeyError:
        raise NoSuchLoadedComponentError("No such loaded component:" + str(name))

def getDevices():
    """
    Returns a pointer to defined devices as a dictionary. From here, you can
    search for a device (see usage below).

    .. note::
    
       This function is documented for reference only. For all modules there
       is already a pre-defined variable containing a pointer to all devices.
       It's **"self._Devices"**.  Usage of this is listed in this example.

    .. warning::

       This returns a pointer to the a dictionary (array) of devices. Care
       should be taken not to remove, replace, or change the dictionary as
       this will affect the entire gateway framework.

    **Short Usage**:

        >>> self._Devices['137ab129da9318']  #by uuid
    or:
        >>> self._Devices['living room light']  #by name

    **Full Usage**:

    .. code-block:: python

       # Get the living room device using the fuzzy search feature.
       livingRoom = self._Devices['living room light']

       # now we can turn on the lamp without needing a pinnumber.
       livingRoom.sendCmd(self, array('skippinnumber':True, 'cmd': 'on'))

    :return: A dictionary of pointers of all devices.
    :rtype: dict
    """
    return getComponent('yombo.gateway.lib.devices')

def getDevice(deviceSearch):
    """
    Returns a pointer to device.
    
    .. note::
    
       This shouldn't be used by modules, instead, use the pre-set point of
       *self._Devices*, see: :py:func:`getDevices`.

    :param deviceSearch: Which device to search for.  DeviceUUID or Device Label. UUID preferred.
    :type deviceSearch: string - Device UUID or Device Label.
    :return: The pointer to the requested device.
    :rtype: object
    """
    return getComponent('yombo.gateway.lib.devices')._search(deviceSearch)

def getDevicesByType():
    """
    Returns a pointer to a **function** to get all devices for a given deviceTypeUUID.
    
    .. note::

       For modules, there is already a pre-defined function for getting all devices
       of a specific type. It's "self._DevicesByType".
    
    **Short Usage**:

        >>> self._DevicesByType('137ab129da9318')  #by device type UUID, this is a function.

    **Usage**:

    .. code-block:: python

       # A simple all x10 lights off (regardless of house / unit code)
       allX10Lamps = self._DevicesByType('137ab129da9318')

       # Turn off all x10 lamps
       for lamp in allX10Lamps:
           lamp.sendCmd(self, array('skippinnumber':True, 'cmd': 'off'))

    :param deviceTypeUUID: The deviceTypeUUID to search for.
    :type deviceTypeUUID: string (uuid)
    :return: Returns a pointer to function that can be called to fetch
        all devices belonging to a device type UUID.
    :rtype: 
    """
    return getattr(getComponent('yombo.gateway.lib.devices'), "getDevicesByType")

def getCommands():
    """
    Returns a pointer to defined commands as a dictionary. From here, you can
    search for a command (see usage below).

    .. note::

       This function is documented for reference only. For all modules there
       is already a pre-defined variable containing a pointer to all commands.
       It's **"self._Commands"**.  Usage of this is listed in this example.

    .. warning::

       This returns a pointer to the a dictionary (array) of commandss. Care
       should be taken not to remove, replace, or change the dictionary as
       this will affect the entire gateway framework.
    
    **Short Usage**:

        >>> self._Commands['se74yhsdSd283']  #by uuid, preferred
    or:
        >>> self._Commands['off']  #by name

    **Full Usage**:

    .. code-block:: python

       from yombo.core.helpers import inputValidate
       # Get the command for "off"
       cmdOff = self._Commands['off']
       # get a device to control.
       bedroomLamp = self._Devices['bedroom light']
       # create a command message
       aMessage = bedroomLamp.getMessage(self, cmdobj=cmdOff)
       #send the message - tell it do it!
       aMessage.send()

    :return: The pointer to the commands dictionary.
    :rtype: dict
    """
    return getComponent('yombo.gateway.lib.commands')

def getCommand(commandSearch):
    """
    Returns a pointer to a command.

    .. note::

       This shouldn't be used by modules, instead, use the pre-set point of
       *self._Commands*, see: :py:func:`getCommands`.

    :param commandSearch: Search for a given command, by cmdUUID or label. cmdUUID is preferred.
    :type commandSearch: string - Command UUID or Command Label.
    :return: The pointer to a single command.
    :rtype: object
    """
    return getComponent('yombo.gateway.lib.commands')._search(commandSearch)
    
def getCommandsByVoice():
    """
    Returns a pointer to all commands by voice as a dictionary. Primary
    used internally.
    
    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getCommandsByVoice
       allVoiceCommands = getCommandsByVoice

    :return: The pointer to all the commands by voice.
    :rtype: dict
    """
    return getComponent('yombo.gateway.lib.commands').getCommandsByVoice()

def getCronTab():
    """
    Returns a pointer to CronTab library.

    .. note::

       This function is documented for reference only. For all modules there
       is already a pre-defined variable containing a pointer:
       **"self._CronTab"**.  Usage of this is listed in this example.

    .. warning::

       This returns a pointer to the a dictionary (array) of commandss. Care
       should be taken not to remove, replace, or change the dictionary as
       this will affect the entire gateway framework.
    
    **Short Usage**:

        >>> self._CronTab['se74yhsdSd283']  #by uuid, preferred
    or:
        >>> self._CronTab['modules.myModule.myCronTabLabel']  #by name

    :return: The pointer to the crontab dictionary.
    :rtype: dict
    """
    return getComponent('yombo.gateway.lib.crontab')

def getVoiceCommands():
    """
    Return the :class:`~VoiceCmd` dictionary (library).  It contains all possible voice
    commands.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getVoiceCommands
       allVoiceCmds = getVoiceCommands()
    
    :see: VoiceCommands_
    :return: Devices object;
    :rtype: object
    """
    return getComponent('yombo.gateway.lib.voicecmds')

def getModule(name):
    """
    Can be used in place of :py:func:`getComponent` to search for
    a module by name or by the module UUID.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getModule
       self.someOtherModule = getComponent("Homevision")

    :raises KeyError: When requested module is not found.
    :param name: The name of the module to find.  Returns a
        pointer to the object so it's functions can be called.
    :type name: string
    :return: The requested object.
    :rtype: Object pointer
    """
    if not hasattr(getModule, 'components'):
        from yombo.lib.loader import getLoader
        getModule.theLoader = getLoader()

    return getModule.theLoader.getModule(name)

def getTimes():
    """
    Returns a pointer to the Times library. This can be used to get various of
    objects in the sky.
    
    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getTimes
       times = getTimes()
       moonrise = times.objRise(dayOffset=1, object='Moon') # 1 - we want the next moon rise

       # Or, assume a module received a status message about a motion detector tripping

       motionDevice = message.payaload['deviceobj'] # get the device from the message
       if times.isDark and motionDevice.status['high']: # it's high if motion detected
         sideYardLight = self._Devices('side yard light')
         sideYardLight.sendCmd(self, array('skippinnumber':True, 'cmd': 'on'))
    
    :return: The pointer to the times object.
    :rtype: object
    """    
    return getComponent('yombo.gateway.lib.times')

def getInterfaceModule(module):
    """
    This function is not fully implemented yet!

    Used by Command/API modules to find it's interface module.
    """
    global yombodbtools
    if yombodbtools == None:
        yombodbtools = get_dbtools()
    iModule = yombodbtools.get_moduleInterface(module._ModuleUUID)
    if (iModule is None):
      return None
    else:
      logger.debug("@#@#:  %s", iModule)
      return 'yombo.gateway.modules.' + iModule.lower()

def getLocalIPAddress():
    """
    Get the ip address of the local machine.

    No single/simple way to do this.  First, do a simple get (works on windows).
    Then if that doesn't work, use the hostname -I function of the os.

    #@TODO: The second method needs to be fixed. Needs to prompt or something
    """
    import socket
    addr = socket.gethostbyname(socket.gethostname())

    badips = ['127.0.0.1', '127.0.1.1']
    
    if addr in badips:
       import commands
       addr = commands.getoutput("hostname -I")

    addr = addr.split()
    addr = addr[0]
    return addr.strip()

def getExternalIPAddress():
    """
    Get the IP address of this machine as seen from the outside world.  THis
    function is primarily used during various internal testing of the Yombo
    Gateway.  This information is reported to the Yombo Service, however, the
    Yombo Service already knows you're IP address during the process of
    downloading configuration files.

    Yombo servers will only use this information if server "getpeer.ip()" function
    results in a private IP address.  See: http://en.wikipedia.org/wiki/Private_network
    This assists in Yombo performing various tests internally, but still providing
    an ability to do further tests.

    Gives Yombo servers a hint of your external ip address from your view. This
    should be the same as what Yombo servers see when you connect.

    This is called only once during the startup phase.  Calling this function too
    often can result in the gateway being blocked by whatismyip.org

    :return: An ip address
    :rtype: string
    """
    import urllib2
    return urllib2.urlopen('http://wtfismyip.com/text').read()

def findKey(symbol_dic, val):
    """
    Find a key of a dictionary for a given key.

    :param symbol_dic: The dictionary to search.
    :type symbol_dic: dict
    :param val: The value to search for.
    :type val: any valid dict key type
    :return: The key of dictionary dic given the value
    :rtype: any valid dict key type
    """
    return [k for k, v in symbol_dic.iteritems() if v == val][0]

def testBit(int_type, offset):
    """
    Tests wether a specific bit is on or off for a given int.

    :param int_type: The given int to interrogate.
    :type int_type: int
    :param offset: The bit location to return, starting from lowest to highest.
    :type offset: int
    :return: If the bit is on or off
    """
    mask = 1 << offset
    if (int_type & mask) > 0:
      return 1
    else:
      return 0
    return(int_type & mask)

def getModuleVariables(moduleName):
    """
    Returns a dictionary of all configurated variables for a module. Modules
    shouldn't call this function as it's already done and set as
    self._ModVariables.

    :param moduleName: Name of module to search for.
    :type moduleName: string
    """
    global yombodbtools
    if yombodbtools == None:
        yombodbtools = get_dbtools()
    return yombodbtools.getVariableModules(moduleName)

def getUserGWToken(username, gwtokenid, fetchRemote=False):
    """
    Fetches a gateway token for a username from yombo service. Used by the
    authention tool when validating users. (UNTESTED!!)

    :param username: Username of user trying to get in.
    :type username: string
    :param gwtokenid: GW Token ID to use for user.
    :type gwtokenid: string
    """
    global yombodbtools
    if yombodbtools == None:
        yombodbtools = get_dbtools()
    record = yombodbtools.getUserGWToken(username, gwtokenid)
    if record == None:
      if fetchRemote == True:
        logger.info("Requesting user tokens.")
        beforeTime = getConfigValue('local', 'lastUserTokens')
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullUsers'}))
        message = {'msgOrigin'      : "yombo.gateway.lib.GatewayConfigs:%s" % getConfigValue("core", "gwuuid"),
                   'msgDestination' : "yombo.svc.lib.GatewayConfigs",
                   'msgType'        : "config",
                   'msgStatus'      : "request",
                   'uuidType'       : "0",
                   'uuidSubType'    : "010",
                   'payload'        : {'cmd' : 'getFullUserGWTokens'},
                  }
        message = Message(**msg)
        message.send()
        for x in range (0,10):
          logger.info("Waiting for user tokens to flow in.")
          sleep(0.2)
          afterTime = getConfigValue('local', 'lastUserTokens')
          if beforeTime != beforeTime:
            recordNew = yombodbtools.getUserGWToken(username, gwtokenid)
            if recordNew != None:
              return recordNew
            else:
              return None
        return None
    else:
      return record

def getModuleDeviceTypes(moduleuuid):
    """
    Returns a dictionary of all device types for a given moduleuuid.

    :param moduleuuid: UUID of the module.
    :type moduleuuid: string
    """
    global yombodbtools
    if yombodbtools == None:
        yombodbtools = get_dbtools()
    return yombodbtools.getModuleDeviceTypes(moduleuuid)

def pgpEncrypt(inText, destination):
    """
    Encrypt text and output as ascii armor text.
    
    :param inText: Plain text to encrypt.
    :type inText: string
    :param destination: Key fingerprint of the destination.
    :type destination: string
    :return: Ascii armored text.
    :rtype: string
    :raises: Exception - If encryption failed.
    """
    if type(inText) is unicode and inText.startswith('-----BEGIN PGP MESSAGE-----'):
        if not hasattr(pgpEncrypt, 'gpgkeyid'):
            pgpEncrypt.gpgkeyid = getConfigValue('core', 'gpgkeyid')
            pgpEncrypt.gpg = gnupg.GPG()

        try:
            output = pgpEncrypt.gpg.encrypt(inText, destination, sign=pgpEncrypt.gpgkeyid )
            if output.status != "encryption ok":
                raise Exception("Unable to encrypt string.")
            return output.data
        except:
            raise Exception("Unable to encrypt string.")
    return inText

def pgpDecrypt(inText):
    """
    Decrypt a PGP / GPG ascii armor text.  If passed in string/text is not detected as encrypted,
    will simply return the input.
    
    #TODO: parse STDERR to make sure the key id is ours. Validates trust.

    :param inText: Ascii armored encoded text.
    :type inText: string
    :return: Decoded string.
    :rtype: string
    :raises: Exception - If decoding failed.
    """

    if type(inText) is unicode and inText.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
        return pgpVerify(inText)
    elif type(inText) is unicode and inText.startswith('-----BEGIN PGP MESSAGE-----'):
        if not hasattr(pgpDecrypt, 'gpgkeyid'):
            pgpDecrypt.gpgkeyid = getConfigValue('core', 'gpgkeyid')
            pgpDecrypt.gpg = gnupg.GPG()
        try:
            out = pgpDecrypt.gpg.decrypt(inText)
            return out.data
        except:
            raise Exception("Unable to decrypt string.")

    return inText


def pgpSign(inText, asciiarmor=True):
    """
    Signs inText and returns the signature.
    """
    #cache the gpg/pgp key locally.
    if type(inText) is unicode or type(inText) is str:
        if not hasattr(pgpSign, 'gpg'):
            pgpSign.gpg = gnupg.GPG()
    
        if not hasattr(pgpSign, 'gpgkeyid'):
            pgpSign.gpgkeyid = getConfigValue('core', 'gpgkeyid')
            pgpSign.gpg = gnupg.GPG()

        try:
            signed = pgpSign.gpg.sign(inText, keyid=pgpSign.gpgkeyid, clearsign=asciiarmor)
            return signed.data
        except:
            raise Exception("Error with GPG system. Unable to sign your message. 101b")
    return False

def pgpVerify(inText):
    """
    Verifys a signature. Returns the data if valid, otherwise False.
    """
    if type(inText) is unicode or type(inText) is str:
        if not hasattr(pgpVerify, 'gpg'):
            pgpVerify.gpg = gnupg.GPG()
    
        try:
            verified = pgpVerify.gpg.verify(inText)
            if verified.status == "signature valid":
                if verified.stderr.find('TRUST_ULTIMATE') > 0:
                    pass
                elif verified.stderr.find('TRUST_FULLY') > 0:
                    pass
                else:        
                    raise Exception("Encryption not from trusted source!")
                out = pgpVerify.gpg.decrypt(inText)              
                return out.data
            else:
                return False
        except:
            raise Exception("Error with GPG system. Unable to verify signed text. 101a")
    return False

def pgpValidateDest(destination):
    """
    Validate that we have a key for the given destination.  If not, try to
    fetch the given key and it to the key ring. Then revalidate.

    .. todo::
    
       This function is mostly a place holder. Function doesn't work or return anything useful.

    :param destination: The destination key to check for.
    :type destination: string
    :return: True if destination is valid, otherwise false.
    :rtype: bool
    """
# Pseudocode
#
# Determine if gateway
# Ask yombo service for keyID of gateway
#   Can just ask keys.yombo.net for it since gateway
#   may have multiple keys - which one to use?
# Wait for yombo service to give us the key id
# Ask gnupg to fetch the key
# Retyrn true if good.
    pass

def pgpDownloadRoot():
    """
    Fetch the latest Yombo root PGP/GPG keyID. Then download it from
    keys.yombo.net. After, mark the key as fully trusted.
    """
    from twisted.web.client import getPage

    environment = getConfigValue("server", 'environment', "production")
    uri = ''
    if getConfigValue("server", 'gpgidtxt', "") != "":
        uri = "http://%s/" % getConfigValue("server", 'gpgidtxt')
    else:
        if(environment == "production"):
            uri = "http://www.yombo.net/gpgid.txt"
        elif (environment == "staging"):
            uri = "http://wwwstg.yombo.net/gpgid.txt"
        elif (environment == "development"):
            uri = "http://wwwdev.yombo.net/gpgid.txt"
        else:
            uri = "http://www.yombo.net/gpgid.txt"

    deferred = getPage(uri)
    deferred.addCallback(pgpCheckRoot)

def pgpCheckRoot(result):
    """
    A callback for :py:meth:`pgpDownloadRoot`. Now that we have Yombo Root
    keyid, lets first check to see if we have already downloaded it this
    session.  If we have, pass. Otherwise, download it and the "fully"
    trust the cert.

    :param result: Result of pgpDownloadRoot is the keyID.
    :type result: string
    """
    if not hasattr(pgpCheckRoot, 'gpg'):
        pgpCheckRoot.gpg = gnupg.GPG()
        pgpCheckRoot.previousID = ""

    rootID = result.strip()

    if rootID == pgpCheckRoot.previousID:
      return
    else:
       pgpCheckRoot.previousID = rootID

    keys = pgpCheckRoot.gpg.list_keys()

    haveRootKey = False

    for key in keys:
      if key['uids'][0][0:12] == "Yombo (Root)":
        if key['keyid'] != rootID:
          pgpCheckRoot.previousID = key['keyid']
        else:
          logger.trace("key (%s) trust:: %s", key['keyid'], key['ownertrust'])
          haveRootKey = True
          if key['ownertrust'] == 'u':
            pass
          elif key['ownertrust'] == 'f':
            pass
          else:
            pgpTrustKey(key['fingerprint'])
        break 

    if haveRootKey == False:
        importResult = pgpCheckRoot.gpg.recv_keys("keys.yombo.net", rootID)
        logger.debug("Yombo Root key import result: %s", importResult)
        pgpTrustKey(key['fingerprint'])
    logger.debug("Yombo Root key. Avail(%s)", haveRootKey)

def pgpCheckKeyTrust(fingerprint):
    """
    Returns the trust level of a given fingerprint.

    :param fingerprint: Fingerprint of keyID to check.
    :type fingerprint: string
    :return: Level of trust.
    :rtype: string

    .. todo::

       NOT DONE!!!  Does not work!!!
    """
    if not hasattr(pgpCheckKeyTrust, 'gpg'):
        pgpCheckKeyTrust.gpg = gnupg.GPG()
    
    keys = pgpCheckKeyTrust.gpg.list_keys()

    logger.info("my keys: %s", keys)
#    return
#    for key in keys:
#      if key['uids'][0][0:12] == "Yombo (Root)":
#        if key['keyid'] != rootID:
#          pgpCheckKeyTrust.previousID = key['keyid']
#        else:
#          logger.info("4444")
#          logger.info("Root key %s", key['keyid'])
#          haveRootKey = True
#          if key['trust'] == 'u':
#            trustRootKey = True
#          else:
#            pgpTrustKey(key['fingerprint'])
#        break 
    

def pgpFetchKey(searchKey):
    if not hasattr(pgpFetchKey, 'gpg'):
        pgpFetchKey.gpg = gnupg.GPG()

    importResult = pgpFetchKey.gpg.recv_keys("keys.yombo.net", searchKey)
    logger.debug("GPG Import result for %s: %s", searchKey, importResult)

def pgpTrustKey(fingerprint, trustLevel = 5):
    """
    Sets the trust of a key.
    #TODO: This function is blocking! Adjust to non-blocking. See below.
    """
    p = Popen(["gpg --import-ownertrust"], shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
    (child_stdout, child_stdin) = (p.stdout, p.stdin)
    child_stdin.write("%s:%d:\n" % (fingerprint, trustLevel))
    child_stdin.close()

    result = child_stdout.read()
    logger.info("GPG Trust change: %s", result)
