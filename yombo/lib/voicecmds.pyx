# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
The term "Voice commands" may be misleading.  Think of voice commands as
noun/verb or verb/noun pairs to control devices.  The verb is the "what",
such as which :class:`~yombo.lib.devices` or module function to send a
:class:`command <yombo.lib.commands>` to. The noun is the "command" that the
device or module should do for the given noun.

Voice commands can be sent in by any means: Speach to text app such as Siri on
iPhone, android speach to text, IM, private (or public if the user is daring)
Twitter feed, Email, SMS, text file monitor, telent input, remote sensor, XPL,
XAP, microphone with speech to text processing capabilities, etc.

**Example**:

  For example, if a voice command noun/verb pairs exit::

    Noun: living room desk lamp
    Verb: on, off, dim, bright

  Then a voice command such as "living room desk light off" would parse as::

    Noun: living room desk lamp
    Verb: off

Two primary actions the voicecmd class can do::

#. Add voice commands
#. Search for voice commands

Users can set voice commands on each device through the API or the
`Yombo Website <http://www.yombo.net>`_ for each device.  The voice commands
are loaded when the gateway starts up.  Additional voice commands can be
added by modules to add more functionality.

Usage
-----

Assume there is a module called "computerTools" that controls various
computer activities.  It could create various commands that allow it to
sleep, power offer, reset, etc. To create additional voice commands,
call the add function with a "command string". The format can either be
'noun [list of verbs]' or '[list of verbs] noun'. The command string
will be parsed the same, regardless of input styple

Can associate a command string to a specific deviceUUID if desired,
however most modules will not set this and leave is as 0. Lastly, the
format, or order, of the voice command can be set. For noun/verb order,
such as "desklamp off", set the "order" variable to "nounverb". For
verb/noun ordering, such as "open garage", set the "order" variable to
"verbnoun". The order can also accept "both" to generate both formats,
however, over use of this will result of more false positives during
the fuzzysearch phase of voice command lookup.
*Avoid the use of "both" when possible.*

**Examples**:

  Adding a voice command for a module in noun/verb order:

  .. code-block:: python

     from yombo.core.helpers import getVoiceCommands
            
     voicecmds = getVoiceCommands()
     voicecmds.add("computer [sleep, hibernate, reset, power off]", 'module.computerTools', 0, 'nounverb')

  Search for the deviceuuid for the desklamp and get the cmdUUID based on the action:
  
  .. code-block:: python

     from yombo.core.helpers import getVoiceCommands
            
     voicecmds = getVoiceCommands()
     voicecmds["desklamb off"] # it's misspelled, but it will still be found.
                               # this return 

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""
import re

from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.exceptions import YomboException
from yombo.core.message import Message
from yombo.core.helpers import getCommands, getCommandsByVoice, getDevices

logger = getLogger('library.voicecmds')

class VoiceCmds(FuzzySearch, YomboLibrary):
    """
    Store all voice commands here and perfrom searches.

    The purpose of this class is two fold: it provides a single repository for
    all possible noun/verb combinations, and provides an ability to *not* have
    to be 100% accurate when looking up noun/verb pairs.

    Convert "voicecmd" strings into voice commands.

    Also, provides searching for voice commands.
    """
    def _init_(self, loader):
        """
        Construct a new VoiceCmds Instance

        items is an dictionary to copy items from (optional)
        limiter is the match ratio below which mathes should not be considered
        """
        self.loader = loader
        super(VoiceCmds, self).__init__(None, .8)
        self.commandsByVoice = getCommandsByVoice()

    def _load_(self):
        """
        Setup self.commandsByVoice.... todo doco...
        """
        self._Devices = getDevices()

    def _start_(self):
        """
        Does notthing, defined to avoid an exception.
        """
        pass

    def _unload_(self):
        """
        Nothing to do.
        """
        pass

    def _stop_(self):
        """
        Nothing to do.
        """
        pass

    def add(self, voiceString, destination, deviceUUID = None, order = 'both'):
        """
        Add a voice command to the available voice commands.

        :raises YomboException: If voiceString or destination is invalid.
        :param voiceString: Voice command string to process: "desklamp [on, off]"
        :type voiceString: string
        :param destination: The destination module or library to send command for processing when activated.
        :type destination: string
        :param kwargs: Multiple key/value pairs.

                 - deviceUUID: (string) The deviceUUID of the item if exists.
                 - order: (string) Order of the voice command.  One of: both, nounverb, verbnoun.
        """
        if voiceString == None or voiceString == None:
            raise YomboException("VoiceString or destination is mising.", 1000, 'voicecmd', 'core')

        tag_re = re.compile('(%s.*?%s)' % (re.escape('['), re.escape(']')))
        stringParts = tag_re.split(voiceString)
        stringParts = filter(None, stringParts) # remove empty bits

        noun = None
        verbs = []

        if len(stringParts) > 2:
            raise YomboException("Cannot have more then 2 string parts for VoiceString.", 1000, 'voicecmd', 'core')

        for part in range(len(stringParts)):
            stringParts[part] = stringParts[part].strip()
            if stringParts[part].startswith("[") and stringParts[part].endswith("]"):
                tempverbs = stringParts[part][1:-1].split(',')
                for verb in range(len(tempverbs)):
                    vtemp = tempverbs[verb].strip()
                    if len(vtemp) > 0:
                        verbs.append(vtemp)
            else:
                noun = stringParts[part]

        if len(verbs) == 0:
            raise YomboException("No verbs found in VoiceString.", 1000, 'voicecmd', 'core')

        for verb in verbs:
            command = self.commandsByVoice[verb]
            a = {}
            if order == 'both':
              a = { "%s %s" % (noun, verb) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'deviceUUID' : deviceUUID,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                        } }
              self.update(a)

              a = { "%s %s" % (verb, noun) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'deviceUUID' : deviceUUID,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                        } }
              self.update(a)

            elif order == 'nounverb':
              a = { "%s %s" % (noun, verb) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'deviceUUID' : deviceUUID,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                        } }
              self.update(a)

            else:
              a = { "%s %s" % (verb, noun) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'deviceUUID' : deviceUUID,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                            'id' : id,
                                        } }
              self.update(a)

    def getMessage(self, voiceCmd, origin = "yombo.gateway.lib.voicecmds"):
        """
        Generates a message that is ready to be sent.

        :param voiceCmd: The result of a voiceCmd search. This will be the payload of the message.
        :type voiceCmd: voiceCmd search results.
        :return: The generated msdUUID
        """
        payload = { 'deviceUUID' : voiceCmd['value']['deviceUUID'],
                    'cmdUUID' : voiceCmd['value']['cmdUUID'],
                  }
        if voiceCmd['value']['deviceUUID'] != None:
            msg = {
            'msgOrigin'      : origin,
            'msgDestination' : "yombo.gateway.modules.%s" % voiceCmd['value']['destination'],
            'msgType'        : "cmd",
            'msgStatus'      : "new",
            'msgStatusExtra' : '',
            'payload'        : payload
            }
            message = Message(**msg)
            return message
        else:
            return self._Devices[voiceCmd['value']['deviceUUID']].getMessage(self, cmdid=voiceCmd['value']['cmdUUID'])
        
