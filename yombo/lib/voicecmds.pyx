# cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see:
  `Voice Commands @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Voice_Commands>`_

The term "Voice commands" may be misleading. Think of voice commands as
noun/verb or verb/noun pairs to control devices. The verb is the "what",
such as which :class:`~yombo.lib.devices` or module function to send a
:class:`command <yombo.lib.commands>` to. The noun is the "command" that the
device or module should do for the given noun.

Voice commands can be sent in by any means: Speach to text app such as Siri on
iPhone, android speach to text, IM, private (or public if the user is daring)
Twitter feed, Email, SMS, text file monitor, telnet input, remote sensor, XPL,
XAP, microphone with speech to text processing capabilities, etc.

**Example**:

  For example, if a voice command has these inputs::

    Noun: living room desk lamp
    Verb: on, off, dim, bright

  Then a string of text with "living room desk light off" would parse as::

    Noun: living room desk lamp
    Verb: off

The voice commands would then generate an "off" command for device
"living room desk lamp".

Two primary actions the voice_cmd class can do:

#. Add voice commands
#. Search for voice commands

Users can set voice commands on each device. The voice commands
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

Can associate a command string to a specific device_id if desired,
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

     voice_cmds = self._Libraries['voicecmds']
     voice_cmds.add("computer [sleep, hibernate, reset, power off]", 'module.computerTools', 0, 'nounverb')

  Search for the device_id for the desklamp and get the cmdUUID based on the action:
  
  .. code-block:: python

     from yombo.core.helpers import getVoiceCommands

     voice_cmds = getVoiceCommands()
     voice_cmds["desklamb off"] # it's misspelled, but it will still be found.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
import re

from yombo.core.exceptions import YomboException
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.message import Message
from yombo.utils import global_invoke_all
from yombo.utils.fuzzysearch import FuzzySearch

logger = get_logger('library.voice_cmds')

class VoiceCmds(FuzzySearch, YomboLibrary):
    """
    Store all voice commands here and perfrom searches.

    The purpose of this class is two fold: it provides a single repository for
    all possible noun/verb combinations, and provides an ability to *not* have
    to be 100% accurate when looking up noun/verb pairs.

    Convert "voice_cmd" strings into voice commands.

    Also, provides searching for voice commands.
    """
    _Name = __class__.__name__
    _FullName = "yombo.gateway.lib.%s" % __class__.__name__


    def _init_(self, loader):
        """
        Construct a new voice_cmds Instance

        items is an dictionary to copy items from (optional)
        limiter is the match ratio below which mathes should not be considered
        """
        self.loader = loader
        super(VoiceCmds, self).__init__(None, .8)
        self.commandsByVoice = self._Libraries['commands']._get_commands_by_voice()

    def _load_(self):
        """
        Setup self.commandsByVoice.... todo doco...
        """
        self._Devices = self._Libraries['devices']

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

    def _module_prestart_(self, **kwargs):
        """
        Implements the _module_prestart_ and is called after _load_ is called for all the modules.

        Expects a list of events to subscribe to.

        **Hooks implemented**:

        * hook_voice_cmds_add : Expects a list of message subscription events to subscrib to.

        **Usage**:

        .. code-block:: python

           def ModuleName_voice_cmds_load(self, **kwargs):
               return ['status']
        """
        voicecommands_to_add = global_invoke_all('voice_cmds_add')
#        logger.info("voicecommands_to_add: {voice_cmds}", voice_cmds=voicecommands_to_add)

        for componentName, voice_cmds in voicecommands_to_add.iteritems():
            if voice_cmds is None:
                continue
            for list in voice_cmds:
                logger.debug("For module '{fullName}', adding voice_cmd: {voice_cmd}, order: {order}", voice_cmd=list['voice_cmd'], fullName=componentName, order=list['order'])
                self.add(list['voice_cmd'], componentName, None, list['order'])

    def search(self, searchFor, limiter_override=None):
        """
        A simple wrapper around fuzzysearch.search to generate stats.

        :param searchFor: The key of the dictionary to search for.
        :type searchFor: int or string
        :param limiter_override: temporarily override the limiter for only this search.
        :return: See description for details
        :rtype: dict
        """
        results = super(VoiceCmds, self).__getitem__(searchFor, limiter_override=None)
        if results['valid'] is True:
            self._Statistics.increment("lib.voicecmds.search.found", bucket_time=30, anon=True)
        else:
            self._Statistics.increment("lib.voicecmds.search.not_found", bucket_time=30, anon=True)
        return results

    def add(self, voiceString, destination, device_id = None, order = 'both'):
        """
        Add a voice command to the available voice commands.

        :raises YomboException: If voiceString or destination is invalid.
        :param voiceString: Voice command string to process: "desklamp [on, off]"
        :type voiceString: string
        :param destination: The destination module or library to send command for processing when activated.
        :type destination: string
        :param kwargs: Multiple key/value pairs.

                 - device_id: (string) The device_id of the item if exists.
                 - order: (string) Order of the voice command.  One of: both, nounverb, verbnoun.
        """
        logger.debug("Adding voice command: {voiceString}", voiceString=voiceString)
        if voiceString is None or voiceString is None:
            raise YomboException("VoiceString or destination is mising.", 1000, 'voice_cmd', 'core')

        tag_re = re.compile('(%s.*?%s)' % (re.escape('['), re.escape(']')))
        stringParts = tag_re.split(voiceString)
        stringParts = filter(None, stringParts) # remove empty bits

        noun = None
        verbs = []

        if len(stringParts) > 2:
            raise YomboException("Cannot have more then 2 string parts for VoiceString.", 1000, 'voice_cmd', 'core')

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
            raise YomboException("No verbs found in VoiceString.", 1000, 'voice_cmd', 'core')

        logger.debug("commands by voice: {commandsByVoice}:{verb}", commandsByVoice=self.commandsByVoice, verb=verb)
        for verb in verbs:
            if verb not in self.commandsByVoice:
                continue
            command = self.commandsByVoice[verb]
            a = {}
            if order == 'both':
              a = { "%s %s" % (noun, verb) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'device_id' : device_id,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                        } }
              self.update(a)

              a = { "%s %s" % (verb, noun) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'device_id' : device_id,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                        } }
              self.update(a)

            elif order == 'nounverb':
              a = { "%s %s" % (noun, verb) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'device_id' : device_id,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                        } }
              self.update(a)

            else:
              a = { "%s %s" % (verb, noun) : { 'noun' : noun, 
                                          'verb' : verb,
                                    'device_id' : device_id,
                                       'cmdUUID' : command.cmdUUID,
                                          'order': 'nounverb',
                                   'destination' : destination,
                                            'id' : id,
                                        } }
              self.update(a)

    def get_message(self, voice_cmd, origin = "yombo.gateway.lib.voice_cmds"):
        """
        Generates a message that is ready to be sent.

        :param voice_cmd: The result of a voice_cmd search. This will be the payload of the message.
        :type voice_cmd: voice_cmd search results.
        :return: The generated msdUUID
        """
        payload = { 'device_id' : voice_cmd['value']['device_id'],
                    'cmdUUID' : voice_cmd['value']['cmdUUID'],
                  }
        if voice_cmd['value']['device_id'] != None:
            msg = {
            'msgOrigin'      : origin,
            'msgDestination' : "yombo.gateway.modules.%s" % voice_cmd['value']['destination'],
            'msgType'        : "cmd",
            'msgStatus'      : "new",
            'msgStatusExtra' : '',
            'payload'        : payload
            }
            message = Message(**msg)
            return message
        else:
            return self._Devices[voice_cmd['value']['device_id']].get_message(self, cmd=voice_cmd['value']['cmdUUID'])
        
