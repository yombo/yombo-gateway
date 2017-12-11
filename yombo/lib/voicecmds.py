# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see:
  `Voice Commands @ Module Development <https://yombo.net/docs/libraries/voice_cmds>`_

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

  Search for the device_id for the desklamp and get the command_id based on the action:
  
  .. code-block:: python

     from yombo.core.helpers import getVoiceCommands

     voice_cmds = getVoiceCommands()
     voice_cmds["desklamb off"] # it's misspelled, but it will still be found.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/voicecmds.html>`_
"""
from inspect import isclass
import re

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import global_invoke_all, random_string
from yombo.utils.fuzzysearch import FuzzySearch

logger = get_logger('library.voice_cmds')

class VoiceCmds(YomboLibrary):
    """
    Store all voice commands here and perfrom searches.

    The purpose of this class is two fold: it provides a single repository for
    all possible noun/verb combinations, and provides an ability to *not* have
    to be 100% accurate when looking up noun/verb pairs.

    Convert "voice_cmd" strings into voice commands.

    Also, provides searching for voice commands.
    """
    def __contains__(self, voice_command_requested):
        """
        Checks to if a provided voice command exists.

            >>> if 'cpu.count' in self._VoiceCmds:

        :raises YomboWarning: Raised when request is malformed.
        :param voice_command_requested: The voice command key to search for.
        :type voice_command_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        if voice_command_requested in self._VoiceCmds:
            return True
        else:
            return False

    def __getitem__(self, voice_command_requested):
        """
        Search for a voice command. this will return a dictionary: id, cmd object, device object.

            >>> voice_command = self._VoiceCmds['living room light on']

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param voice_command_requested: The voice command key to search for.
        :type voice_command_requested: string
        :return: dict containing: 'id', 'cmd', 'device'
        :rtype: dict
        """
        return self.get(voice_command_requested)

    def __setitem__(self, voice_command_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, voice_command_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter voice commands. """
        return self.__yombocommands.__iter__()

    def __len__(self):
        """
        Returns an int of the number of voice commands defined.

        :return: The number of voice commands defined.
        :rtype: int
        """
        return len(self.__yombocommands)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo voice commands library"

    def keys(self):
        """
        Returns the keys of the voice commands that are defined.

        :return: A list of voice commands defined. 
        :rtype: list
        """
        return list(self.__yombocommands.keys())

    def items(self):
        """
        Gets a list of tuples representing the voice commands defined.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.__yombocommands.items())

    def iteritems(self):
        return iter(self.__yombocommands.items())

    def iterkeys(self):
        return iter(self.__yombocommands.keys())

    def itervalues(self):
        return iter(self.__yombocommands.values())

    def values(self):
        return list(self.__yombocommands.values())

    def _init_(self, **kwargs):
        """
        Construct a new voice_cmds Instance

        items is an dictionary to copy items from (optional)
        limiter is the match ratio below which mathes should not be considered
        """
        self.voice_command_strings = FuzzySearch(None, .80)
        self.voice_command_data = {}

        self.commandsByVoice = self._Commands.get_commands_by_voice()

    @inlineCallbacks
    def _modules_loaded_(self, **kwargs):
        """
        Implements the _modules_loaded_ and is called after _load_ is called for all the modules.

        Expects a list of events to subscribe to.

        **Hooks called**:

        * _voicecmds_add_ : Expects a list of message subscription events to subscrib to.

        **Usage**:

        .. code-block:: python

           def ModuleName_voice_cmds_load(self, **kwargs):
               return ['status']
        """
        voicecommands_to_add = yield global_invoke_all('_voicecmds_add_', called_by=self)
#        logger.info("voicecommands_to_add: {voice_cmds}", voice_cmds=voicecommands_to_add)

        for componentName, voice_cmds in voicecommands_to_add.items():
            if voice_cmds is None:
                continue
            for list in voice_cmds:
                logger.debug("For module '{fullName}', adding voice_cmd: {voice_cmd}, order: {order}", voice_cmd=list['voice_cmd'], fullName=componentName, order=list['order'])
                self.add_by_string(list['voice_cmd'], list['call_back'], list['device'], list['order'])

    def get_all(self):
        """
        Returns a list of voice commands.
        :return:
        """
        results = {}
        for voice, voice_id in self.voice_command_strings.items():
            results[voice] = self.voice_command_data[voice_id]
        return results

    def get(self, voice_command_requested, limiter_override=None):
        """
        Search for a voice command. this will return a dictionary: id, cmd object, device object.

        You can use the device and command objects as desired.

            >>> self._VoiceCmds['living room light on']  #by name

        :param voicecmd_requested: Search all available voice commands for a phrase.
        :type voicecmd_requested: string
        :return: dict containing: 'id', 'cmd', 'device'
        :rtype: dict
        """
        try:
            result = self.voice_commands.search2(voice_command_requested, limiter_override=limiter_override)
            self._Statistics.increment("lib.voicecmds.search.found", bucket_size=30, anon=True)
            return self.voice_command_data[result]
        except:
            self._Statistics.increment("lib.voicecmds.search.not_found", bucket_size=30, anon=True)
            raise KeyError("Searched for voice command, none found: %s" % voice_command_requested)

    def add_by_string(self, voice_string, call_back = None, device = None, order = 'devicecmd'):
        """
        Adds a voice command by using a string like "desk lamp [on, off]". This will add the following voice commands
        based on the value of 'order'.  If both is provided, the following will be added:

        * desklamp on
        * desklamp off
        * off desklamp
        * on desklamp

        You can specify 'order' as: both, devicecmd, cmddevice. This determines what ordering the voice commands
        are added. In the above example, specifying 'devicecmd', then only the first two items are added.

        Either a callback function must be provided or a device must be provided. Otherwise, the voice command
        will not be added and a YomboWarning will be raised if either or both are defined.

        :raises YomboWarning: If voiceString or destination is invalid.
        :param voice_string: Voice command string to process: "desklamp [on, off]"
        :type voice_string: string
        :param call_back: A function to send the voice command id, device, and command objects to.
        :type call_back: pointer to function
        :param device: A device id or device label to search for a matching device.
        :type device: string
        :param order: The ordering in which to add voice command text lookup. Default: devicecmd
        :type order: string
        """
        logger.debug("Adding voice command: {voice_string}", voice_string=voice_string)
        if call_back is None and device is None:
            raise YomboWarning("'call_back' and 'device' are mising.", 1000, 'add_by_string', 'voicecmds')

        if call_back is not None and device is not None:
            raise YomboWarning("Either specifiy 'call_back' or 'device', not both.", 1001, 'add_by_string', 'voicecmds')

        try:
            tag_re = re.compile('(%s.*?%s)' % (re.escape('['), re.escape(']')))
            string_parts = tag_re.split(voice_string)
            string_parts = [_f for _f in string_parts if _f] # remove empty bits

            device_obj = None
            if device is not None:
                if isclass(device):
                    device_obj = device
                else:
                    device_obj = self._Devices[device]

            commands = []
        except:
            raise YomboWarning("Invalid format for 'voice_string'", 1010, 'add_by_string', 'voicecmds')


        if len(string_parts) > 2:
            raise YomboWarning("Invalid format for 'voice_string'", 1003, 'add_by_string', 'voicecmds')

        for part in range(len(string_parts)):
            string_parts[part] = string_parts[part].strip()
            if string_parts[part].startswith("[") and string_parts[part].endswith("]"):
                temp_commands = string_parts[part][1:-1].split(',')
                for cmd in range(len(temp_commands)):
                    cmd_temp = temp_commands[cmd].strip()
                    if len(cmd_temp) > 0:
                        commands.append(cmd_temp)
            else:
                device_label = string_parts[part]

        if len(commands) == 0:
            raise YomboWarning("No commands found in voice_string.", 1003, 'add_by_string', 'voicecmds')

        # logger.debug("commands by voice: {commandsByVoice}:{verb}", commandsByVoice=self.commandsByVoice, verb=verb)
        for cmd in commands:
            if cmd not in self.commandsByVoice:
                continue
            command = self.commandsByVoice[cmd]
            vc_id = random_string(length=12)

            if order == 'both':
                self.voice_command_strings["%s %s" % (device_label, cmd)] = vc_id
                self.voice_command_strings["%s %s" % (cmd, device_label)] = vc_id

            elif order == 'devicecmd':
                self.voice_command_strings["%s %s" % (device_label, cmd)] = vc_id

            else:
                self.voice_command_strings["%s %s" % (cmd, device_label)] = vc_id

            self.voice_command_data[vc_id] = {
                'id': vc_id,
                'cmd': command,
                'device': device_obj,
                'call_back': call_back
            }
