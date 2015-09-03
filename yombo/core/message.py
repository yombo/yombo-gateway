# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
The Yombo Message is a key component or concept for the Yombo system.  Yombo
messages are used to communicate between all components.  This includes within
a gateway, and between the gateway and any other endpoints, such as the Yombo
service. 

Internally to the gateway software, the Yombo Message is responsible for
delivering commands and status updates to various libraries and modules for
further processing.  Externally, it is used to send commands to/from control
software, and to Yombo servers for configuration.  It can also be used
to send messages to other gateways with commands to control remote
devices.

Other than a standard set of key components, the yombo message is fairly free
form. Module developers should follow these guidelines when developing modules
so that they can communicate with other modules.  If additional standards or
fields are needed, please start a new thread on the forums for discussion.

Additionally, 'product family types' such as X10, Insteon, Z-Wave, Audio,
Video, may have additional requirements.  See
`here for additional details <https://projects.yombo.net/projects/modules/wiki>`_

TODO: Document standard payload fields here.

.. module:: yombo.core.message
   :synopsis: Yombo Messages are a key item for managing automation devices.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2015 by Yombo
:license: RPL 1.5, see LICENSE for details.
"""
# Import python libraries
from collections import OrderedDict
from json import dumps, loads
from uuid import uuid4
import copy
import time

# Import twisted libraries
from twisted.internet.reactor import callLater

# Import Yombo libraries
from yombo.core.exceptions import YomboMessageError
#TODO: When redoing PGP, move calls to the library
from yombo.core.helpers import getConfigValue, getComponent, generateUUID, getCommand, getDevice, pgpSign, pgpVerify
from yombo.core.log import getLogger
from yombo.lib.loader import getLoader

logger = getLogger('core.message')

class Message:
    """
    The message class is responsible for handling all message activities.  It
    distributes messages to various modules depending on message subscriptions
    as well as to specific modules that handle a specific device as defined in
    the message.
    """

    def __init__(self, **kwargs):
        """
        Generate a message from a dictionary. If using to control a device,
        it's best to use the device instanct to send messages.

        The params defined refer to kwargs and become class variables.
        
        :param msgOrigin: **Required.** Library, module, or other component
            that generated the message. This will be used to send a reply
            message if needed.  It is also used for GPG/PGP key selection for
            validating/decrypting commands and status messages sent from remote
            places.
        :type msgOrigin: string
        :param msgDestination: **Required.** The final destination for the
            message. If the message cannot be delivered to the destination,
            a return message will be sent to the Origin with the same
            messageID with a status of "failed".  An exception is not thrown
            since it may take a while to get a failed message.
        :type msgDestination: string
        :param msgType:           logger.info("messages:beforeSendMessage")
The type of message being sent, such as: command,
            event, status, config:

            * "cmd" - Used for sending commands to various devices. It is best
              to use Device library to complete this.
            * "voiceCmd" - Used by the voiceCmd module to send a registered
              voiceCmd to a module. This is used if the voiceCmd doesn't match
              a deviceUUID.
            * "event" - Used to send various system events. (TODO: make a list!)
            * "status" - Used for sending device status.  This is typically used
              by Device object to send status when something is changed.
            * "config" - Only used by Yombo  servers to send configuration
              information to configurationupdate library. Typically, these type
              of messages pass through this library for performance reasons.
              Modules should not be sending config messages. If a configuration
              item is needed, use the Helper library.
        :type msgType: string
        :param msgStatus: **Required.** Status of this message (value depends
            on the msgType), such as - new, process, done, failed, reply:

            * Reply type messages must include the previous msgUUID so the
              sender can match the request.
            * For cmd (command):
           
                * "new" - A new command request. A new unqiue msgUUID must be
                   generated.
                * "processing" - A reply type message.  Sent by a receiving
                   module if the command request is taking longer than 1 second
                   to complete.
                * "done" - A reply type message noting that a previous command
                   was completed successfully. A separate "status" message
                   should be sent if a device's state has changed.  This is
                   handled by the Devices library.  msgStatusExtra can contain
                   additional notes. A payload of the reply message should have
                   an item of "textStatus" for human consumption. It can also
                   have "textStatusExtra, also formatted for humans.
                * "delayed" - notBefore was set, message was marked for a future
                   delivery time.  Another message can follow in the future
                   if the receiving module/library knows how.
                * "failed" - A reply type message.  Sent by a receiving module
                   if the request failed.  See msgStatusExtra for details.
                * "reply" - A reply type message.  Sent by a receiving module if
                   it needs to send some sort of message back to the sending
                   module.
            * For status:
           
                * "device" - Device status update. Change in device state.
                * "info" - For information only. Might be displayed in a log
                   file or some other occasionally monitored item. Perhaps
                   a daily email of all info's will be sent to user.
                * "notice" - Notice that should be delivered to user. Displayed
                   on screens, or connected controllers.  Such as new email.
                * "warning" - More important than a notice, treated the same
                   as a notice but with more urgency.
                * "alert" - Something critical. An alarm going off. This
                   can include a notice to be sent via SMS or other method
                   for more immediate attention.
            * For event:
            
                * "nowDark" - It's now dark outside, not even twilight.
                * "nowNight" - The center of sun is below horizon
                * "nowLight" - The sun is up, or is twilight
                * "nowDay" - The center of the sun is above horizon.
                * "nowDawn" - The time it's twilight, but before sunrise
                * "nowNotDawn" - It's now longer nowDawn
        :type msgStatus: string
        :param msgStatusExtra: Optional, except required for "reply" and
            "failed" of "msgStatus" types. Otherwise, used as an extra status
            information, used for human display or logging.
        :type msgStatusExtra: string
        :param textStatus: Optional. Human readable form of status.
        :type textStatus: string
        :param uuidType: Help identify what function generated the message,
            default is 'z'.
        :type uuidType: string
        :param uuidSubType: Extended identification, up to three hex characters,
            default is 'zzz'.
        :type uuidSubType: string
        :param msgUUID: Only required for messages that are considered 'reply
            type' messages, if blank, a new msgUUID will be generated.
        :type msgUUID: string
        :param payload: Message payload to be processed by the library or module.
        
               * cmd message: Must include one of the follow, in order of preference:

                   * "command" (preferred) - A refered to the command object.
                   * "cmdUUID" - UUID of the command.
                   * "cmd" to identify what command

                   * Must also include "device" (a reference to a device object) or
                     "deviceUUID".

               * status message: Must include: 

                   * "deviceUUID"
                   * "status" (namedtuple::Status) Contains time, statusextra, settime, source.
                   * "prevStatus" (string) The previous status.

        :type payload: dict
        :param msgOrigUUID: Used for sending replies. Used so the receiver
               knows what the original msgUUID was for tracking purposes.
        :type msgOrigUUID: string
        :param msgPath: Used to track the history of the message. Most recent
            entry at the end.
        :type msgPath: OrderedDict

        :param sentTo: Only used within a gateway, it notes what modules this
               message has been sent to. Populated during message distribution.
        :type sentTo: dict        The params defined refer to kwargs.
        
        :param notBefore: Time in unix epoch to wait before deliverying the
            message. Used as a way to defer delivery of a message until epoch
            has _passed_.  Note: This is not a delay in number of seconds, but
            a time in number of seconds since epoch.  Messages with a notBefore
            are persisted between gateway restarts.
        :type notBefore: int

        :param maxDelay: Used with notBefore. A window of time (in seconds) that
            the message can be delivered in.  Another way of thinking: the
            maximum number of seconds since notBefore that can pass before the
            message expires and not be delivered. This occurs if the gateway
            is down during the time the notBefore time elapses.
        :type maxDelay: int

        :param msgAuth: Used when processing non-local messages. Used to
            validate the source of a remotely generated message. This
            dictionary *can* contain the following attributes:

            * "signature" (Required) - PGP/GPG ascii armored signature of the
               following attributes: msgOrigin, msgDestination, msgType,
               msgStatus, msgStatusExtra, msgUUID, payload, msgAuth.username,
               msgAuth.type.
            * "username" (Optional) - If the receiving component requires the
               user to be authenticated, this field will be populated with
               the username. Used for API calls or remote data streams such as
               HTML5 clients, etc.
        :type msgAuth: dict

        :param newMessage: Default is True. Set to false to force simple
            validations on the message. For example, it will make sure the
            msgUUID exists and won't create a new one.
        :type newMessage: bool
        """
        self.loader = getLoader()
        self.libMessages = getComponent('yombo.gateway.lib.messages')

        self.msgOrigin      = kwargs['msgOrigin']
        self.msgDestination = kwargs['msgDestination']
        self.msgType        = kwargs['msgType']
        self.msgStatus      = kwargs['msgStatus']
        self.msgStatusExtra = kwargs.get('msgStatusExtra')
        self.textStatus     = kwargs.get('textStatus')
        self.uuidType       = kwargs.get('uuidType', 'z')
        self.uuidSubType    = kwargs.get('uuidSubType', 'z')
        self.msgUUID        = kwargs.get('msgUUID')
        self.msgOrigUUID    = kwargs.get('msgOrigUUID')
        self.payload        = kwargs['payload']
        self.msgAuth        = kwargs.get('msgAuth', {})
        self.msgPath        = OrderedDict([])
        self.notBefore      = kwargs.get('notBefore', 0)
        self.maxDelay       = kwargs.get('maxDelay', 0)
        self.newMessage     = kwargs.get('newMessage', True)

        if 'msgPath' in kwargs:
            for hop in kwargs['msgPath']:
                self.msgPath[hop] = kwargs['msgPath'][hop]

        self.sentTo = []

        self.gwUUID = getConfigValue("core", "gwuuid")
        if self.msgUUID == None:
          if self.newMessage:
            self.msgUUID = str(generateUUID(mainType=self.uuidType, subType=self.uuidSubType))
          else:
            raise YomboMessageError("Existing message should have a msgUUID", 'Message API::Create message.')

    def __getitem__(self, key):
        """
        Simulate a dictionary lookup of a key value. Typical usage::

            message['msgOrigin']

        :param key: The key, or item, to lookup within the message.
        :type key: C{dict} or C{int}
        :return: The attribute requested for by "key".
        :rtype: string
        """
        return getattr(self, key)

    def dump(self):
        """
        Return the message objects as a dictionary. The resulting dictionary
        can be used create a new message, for display, etc.

        :return: A dictionary containing the key values of the message. Can be
            used to create a new message.
        :rtype: dict

        """
        return {'msgOrigin'     : str(self.msgOrigin),
                'msgDestination': str(self.msgDestination),
                'msgType'       : str(self.msgType),
                'msgStatus'     : str(self.msgStatus),
                'msgStatusExtra': str(self.msgStatusExtra),
                'msgUUID'       : str(self.msgUUID),
                'uuidType'      : str(self.uuidType),
                'uuidSubType'   : str(self.uuidSubType),
                'msgUUID'       : str(self.msgUUID),
                'msgOrigUUID'   : str(self.msgOrigUUID),
                'msgPath'       : str(self.msgPath),
                'sentTo'        : str(self.sentTo),
                'msgAuth'       : dict(self.msgAuth),
                'notBefore'     : int(self.notBefore),
                'maxDelay'      : int(self.maxDelay),
                'payload'       : dict(self.payload),
                }

    def dumpToExternal(self):
        """
        Used to create a dictionary to send the message external.
        
        TODO: Create a message signature HASH Using gpg
        """

        newmsg = { 'msgDestination' : msg['msgDestination'],
                   'msgOrigin'      : msg['msgOrigin'],
                   'data'           : {},
                 }
        msgItemsSkip = ( 'msgOrigin', 'msgDestination', 'uuidType', 'uuidSubType', 'notBefore', 'maxDelay')
        for item in msg:
            if item in msgItemsSkip:
                continue
            newmsg['data'][item] = msg[item]
        return newmsg

    def getReply(self, **kwargs):
        """
        Using the current message, generate a new message skeleton most fields
        prepopulated. This is typically used to generate a reply. Usage::

            newMessage = existingMessage.getReply(msgStatus="done", textStatus="Process has completed.")
            newMessages.payload = newPayload
            newMessage.send()

        :return: A new message object with the msgOrigin fliped with
            msgDestination.
        :rtype: message
        """
        repl = {
            'msgOrigin'      : self.msgDestination,
            'msgDestination' : self.msgOrigin,
            'msgType'        : self.msgType,
            'msgOrigUUID'    : self.msgUUID,
            'msgStatus'      : kwargs.get('msgStatus', 'reply'),
            'msgStatusExtra' : kwargs.get('msgStatusExtra', None),
            'payload'        : {},
            }
        if 'textStatus' in kwargs:
            repl['textStatus'] = kwargs['textStatus']
        reply = Message(**repl)
        return reply

    def send(self):
        """
        Send a message that has it's fields already popualted.

        If this is a local message, it will send itself to the "msgDestination"
        as well as any libraries and modules that have requested message
        distributions for this message type.

        The messages will be validated by :py:func:`validateMessage` function
        before being sent, it may raise a :py:func:`yombo.core.exceptions.MessageError`.

        :raise YomboMessageError: When the message cannot be sent and the reason why.
        :return: True if sent, otherwise will toss an exception.
        ":rtype: bool
        """
        if self.validateMessage() == False:
            raise YomboMessageError("You should never see this message. If you do.  Please tell supprt@yombo.net about it!", 'Message API::Catchall')

        if self.checkDestinationAsLocal() == False:
            gc = getComponent('yombo.gateway.lib.gatewaycontrol')
            gc.message(self)
            logger.info("message is not marked for local. Sending to server for processing!")
            return
        if self.msgType == "control": # control messages
            if self.cmd == "disconnectSvc":
# TODO: finish this!
                self.loader.loadedComponents['yombo.gateway.lib.GatewayControlProtocol']

                
        if self.libMessages.processing == False:
            logger.debug("Message::send - Queuing message for later")
            self.libMessages.queue.appendleft(self)
            return

        # if message is to be delievered later, send to queue
        if self.notBefore > time.time():
            self.libMessages.addToDelay(self)
            return

        # Now we are ready to send the message.  First tell messages library.
        self.libMessages.beforeSendMessage(self)

        #first send to target, then to distro lists
        destParts = self.msgDestination.split(".")
        allComponents = copy.copy(self.loader.loadedComponents)
        if self.msgDestination in allComponents:
            component = allComponents[self.msgDestination]

            self.sentTo.append(self.msgDestination)
            callLater(0.00001, component.message, self)
#	            ret = component.message(self)                     # send actual message
            del allComponents[self.msgDestination]
        else:
            if destParts[2] != "all":
                logger.error("Send message: Invalid destination for message. Asked to send it to: %s", self.msgDestination)
                # TODO: Perhaps send reponse to sender...security??
                return

        #second, send to distribution lists. If list exists, and not already sent.
        if self.msgType != "unknown":
            if self.msgType in self.libMessages.distributions:  # make sure dist exists
                for componentName in self.libMessages.distributions[self.msgType]:
                    if componentName in allComponents:   # make sure it's not already sent
                        component = allComponents[componentName]
                        callLater(0.00001, component.message, self)
                        self.sentTo.append(componentName)
                        del allComponents[componentName]  # remove, won't send again

        #third, send to distrubution "all" last.
        logger.debug("message - sending to all distro list: %s", self.libMessages.distributions)
        if "all" in self.libMessages.distributions and (self.msgStatus == 'new' or self.msgType == 'event'):  # make sure dist exists
            for componentName in self.libMessages.distributions["all"]:
                if componentName in allComponents:   # make sure it's not already sent
                    component = allComponents[componentName]
                    callLater(0.00001, component.message, self)
                    self.sentTo.append(componentName)
                    del allComponents[componentName]  # remove, won't send again

    def addPath(self, component, external):
        """
        Append an entry to the msgPath.  Will automatically append the gateway
        UUID to the end of the component if it's 'yombo.gateway' to start.
        
        If you are receiving this from an external source, such as a remote
        controller, make sure to call this method twice - once with the
        controller origin with external as True and then again with the
        receiving component name with external marked as False.
        
        :param component: The full name of the component. Eg: yombo.gateway.modules.homevision
        :type component: string
        :param external: True if the packet came from an external source, otherwise false if generated internally.
        :type external: bool
        :raise YomboMessageError: If external is not a True or False.  Also raised if component doesn't start with
        'yombo.gateway' and doesn't include the remotes UUID.  IE: yombo.controller:s83h8109d81h0dh213
        """

        component = component.lower()
        parts = component.split(":")

        components = parts[0]
        if component[:13] == "yombo.gateway":
           component = "%s:%s" % (component, self.gwUUID)
        else:
           raise YomboMessageError("Component name must start with 'yombo.gateway'.", 'Message API')
        
        self.msgPath[str(uuid4)] = {'component' : component, 'external' : external}
        
    def addPathLocal(self, component, external):
        """
        A simple wrapper that prepends "component" with "yombo.gateway." before sending to addPath.

        :param component: The library or module name after "yombo.gateway". IE: modules.controler.UserName
        :type component: string
        :param external: True if the packet came from an external source, otherwise false if generated internally.
        :type external: bool
        """
        component = "yombo.gateway.%s" % (component,)
        self.addPath(component, external)
        
    def update(self, updateDict):
        """
        Update many items in one swoop.  Usually used when array is sent to
        us from an outside source.

        :param updateDict: A dictionary of various message class components to update.
        :type updateDict: dict
        """
        logger.trace("MESAGE.update(%s)", updateDict)
        checkLocalDest = False
        for k, v in updateDict.iteritems():
            if k == "msgOrigin":
                self.msgOrigin = v
            elif k == "msgDestination":
                self.msgDestination = v
            elif k == "msgType":
                self.msgType = v
            elif k == "msgStatus":
                self.msgStatus = v
            elif k == "msgStatusExtra":
                self.msgStatusExtra = v
            elif k == "msgUUID":
                self.msgUUID = v
            elif k == "uuidType":
                self.uuidType = v
            elif k == "uuidSubType":
                self.uuidSubType = v
            elif k == "payload":
                self.payload = v
            elif k == "notBefore":
                self.notBefore = v
            elif k == "maxDelay":
                self.maxDelay = v
            else:
              raise YomboMessageError("Item '%s' is not a valid message component" % (k,), 'message API')

    def validateMessage(self):
        """
        Validates the content of messages before sending.

        For command (cmd) type messages, it makes sure the message makes sense.
        For example, it checks that the cmd and cmdUUID match, and that command
        is legitimate for the given deviceUUID.

        Also checks valid deviceUUID, etc.
        :return: True if the message is valid.
        :rtype: bool
        """
        self.msgDestination = self.msgDestination.lower()
        self.msgOrigin = self.msgOrigin.lower()

#        self._validateRouting()

#todo: update for routing messages to other gateways

        if self.msgType == "cmd":  # commands for devices
          self.__validateCmd()
        elif self.msgType == "status": #device status changes
          self.__validateStatus()
#        elif self.msgType == "event": #device status changes
#          return self.__validateEvent()

        # if origin isn't local, check for msgAuth and validate it.
        if self.checkOriginAsLocal() == False:
            self.validateMsgAuth()
        return True

    def checkDestinationAsLocal(self):
        """
        Check if the message has a destination for the local gateway.

        :raise YomboMessageError: If the msgDestination is missing or invalid.
        :return: True if the message is for this gateway, otherwise false.
        :rtype: C{bool}
        """
        isLocal = False
        dest = self.msgDestination.split(":")
        if len(dest) == 1:
            if str(self.msgDestination[:13]).lower() == "yombo.gateway":
                isLocal = True
        elif len(dest) == 2:
            if str(self.msgDestination[:13]).lower() == "yombo.gateway" and dest[1] == self.gwUUID:
                isLocal = True
        else:
            raise YomboMessageError('msgDestination is missing or invalid. msgDestination: %s' % self.msgDestination, 'Message API')
        return isLocal

    def checkOriginAsLocal(self):
        """
        Used to validate that the message was generated locally. Checks both destination
        and msgPath to validate it didn't some how sneak in from an external source.
        
        :raise YomboMessageError: If the msgOrigin is missing or invalid.
        :return: True if the message was generated locally, otherwise False from external.
        :rtype: bool
        """
        for hop in self.msgPath:
            if self.msgPath[hop]['external'] == 'yes':
                return False  # it's marked as not being us
            origin = self.msgPath[hop]['component']
            parts = origin.split(":")
            if len(parts) == 1:
                if str(self.msgOrigin[:13]).lower() != "yombo.gateway":
                    return False # it's not even a gateway, so can't be us
            elif len(parts) == 2:
                if str(self.msgOrigin[:13]).lower() != "yombo.gateway" and parts[1] != self.gwUUID:
                    return False  # It's not us!
            else:
                raise YomboMessageError('msgOrigin is missing or invalid. msgOrigin: %s' % self.msgOrigin, 'Message API')
        return True

    def __validateCmd(self):
        """
        Helper function for :py:func:`validateMessage` to validate command messages.
        """
        if self.msgStatus != 'new':
            return True
        
        logger.trace("validcmd payload: %s" % self.payload)

        #for testing with isinstance. Can't include at startup - loop!
        from yombo.lib.devices import Device
        from yombo.lib.commands import Command

        if 'cmdobj' in self.payload:
            if isinstance(self.payload['cmdobj'], Command):
              self.payload['cmdUUID'] = self.payload['cmdobj'].cmdUUID
              self.payload['cmd'] = self.payload['cmdobj'].cmd
            else:
              raise YomboMessageError("if 'cmdobj' specified', it must be a command instance.", 'Message API::ValidateCMD')
        elif 'cmdUUID' in self.payload:
            try:
              self.payload['cmdobj'] = getCommand(self.payload['cmdUUID'])
              self.payload['cmdUUID'] = self.payload['cmdobj'].cmdUUID
              self.payload['cmd'] = self.payload['cmdobj'].cmd
            except:
              raise YomboMessageError("Couldn't find specified cmdUUID.", 'Message API::ValidateCMD')
        elif 'cmd' in self.payload:
            try:
              self.payload['cmdobj'] = getCommand(self.payload['cmd'])
              self.payload['cmdUUID'] = self.payload['cmdobj'].cmdUUID
              self.payload['cmd'] = self.payload['cmdobj'].cmd
            except:
              raise YomboMessageError("Couldn't find specified cmd.", 'Message API')
        else:
            raise YomboMessageError("'cmdobj', cmdUUID', or 'cmd' not found in payload. Required for commands.", 'Message API::ValidateCMD')
        

        # only perform the following checks if message is for local gateway!!
        localParts = self.msgDestination.split(":")
        if(len(localParts) != 1):
            return True

        # check deviceUUID
        if 'deviceobj' in self.payload:
            if isinstance(self.payload['deviceobj'], Device):
              self.payload['deviceUUID'] = self.payload['deviceobj'].deviceUUID
              self.payload['device'] = self.payload['deviceobj'].label
            else:
              raise YomboMessageError("if 'deviceobj' specified', it must be a device instance.", 'Message API::ValidateCMD')
        elif 'deviceUUID' in self.payload:
            try:
              self.payload['deviceobj'] = getDevice(self.payload['deviceUUID'])
              self.payload['deviceUUID'] = self.payload['deviceobj'].deviceUUID
              self.payload['device'] = self.payload['deviceobj'].label
            except:
              raise YomboMessageError("Couldn't find specified deviceUUID.", 'Message API')
        elif 'device' in self.payload:
            try:
              self.payload['deviceobj'] = getDevice(self.payload['device'])
              self.payload['deviceUUID'] = self.payload['deviceobj'].deviceUUID
              self.payload['device'] = self.payload['deviceobj'].label
            except:
              raise YomboMessageError("Couldn't find specified deviceUUID.", 'Message API')
        else:
            raise YomboMessageError("'deviceUUID' or 'device' not found in payload. Required for commands.", 'Message API::ValidateCMD')

        logger.trace("availablecommands: %s" % self.payload['deviceobj'].availableCommands)
        logger.trace("self.payload['cmdobj']" % self.payload['cmdobj'])
        # check that command is possible for given deviceUUID
        if self.payload['cmdobj'].cmdUUID not in self.payload['deviceobj'].availableCommands:
           raise YomboMessageError("Invalid cmdUUID for this deviceUUID.", 'Message API::ValidateCMD')

        # force delivery to the correct module.
        if(self.msgStatus == "new"):
            moduleLabel = "yombo.gateway.modules." + self.payload['deviceobj'].moduleLabel.lower()
            if(self.msgDestination != moduleLabel):
                self.msgDestination = moduleLabel

    def __validateStatus(self):
        """
        Helper function for :py:func:`validateMessage`. Handles status messages.
        """
        return True

    def __validateEvent(self):
        """
        Helper function for :py:func:`validateMessage`. Handles event messages.
        """
        return True

    def generateMsgAuth(self, **kwargs):
        """
        Generates and sets the msgAuth dictionary.

        The params defined refer to kwargs.

        :param username: Username that is authenticated. Usually
            used from remote connections.
        :type username: string
        """
        if 'signature' in self.msgAuth:
            del self.msgAuth['signature']

        hashed = { 'msgOrigin' : str(self.msgOrigin),
                   'msgDestination' : str(self.msgDestination),
                   'msgType' : str(self.msgType),
                   'msgStatus' : str(self.msgStatus),
                   'msgStatusExtra' : str(self.msgStatusExtra),
                   'msgUUID' : str(self.msgUUID),
                   'msgAuth' : self.msgAuth,
                   'payload' : self._generatePayloadHash(),
                 }

        self.msgAuth['username'] = kwargs.get('username', '')
        self.msgAuth['signature'] = pgpSign(dumps(hashed))

    def validateMsgAuth(self):
        """
        Validates that the message authentication is valid.
        """
        if 'signature' in self.msgAuth:
            hash = loads(pgpVerify(self.msgAuth['signature']))
            logger.trace(hash)
            if self.msgOrigin != hash['msgOrigin']:
                raise YomboMessageError("msgOrigin doesn't match hash.", 'Message API::ValidateMsgAuth')
            if self.msgDestination != hash['msgDestination']:
                raise YomboMessageError("msgDestination doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgType) != hash['msgType']:
                raise YomboMessageError("msgType doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgStatus) != hash['msgStatus']:
                raise YomboMessageError("msgStatus doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgStatusExtra) != hash['msgStatusExtra']:
                raise YomboMessageError("msgStatusExtra doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgUUID) != hash['msgUUID']:
                raise YomboMessageError("msgUUID doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgAuth['username']) != hash['msgAuth']['username']:
                raise YomboMessageError("username doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self._generatePayloadHash()) != hash['payload']:
                raise YomboMessageError("payload doesn't match hash.", 'Message API::ValidateMsgAuth')

    def _generatePayloadHash(self):
        """
        Using various message variables to generate an auth hash.
        """
        import hashlib
        aList = sorted(self.payload)
        aString = ""
        for anItem in aList:
            aString = aString + self.payload[anItem]
        return hashlib.sha256(aString).hexdigest()
