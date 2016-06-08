# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
The Yombo Message is a key component or concept for the Yombo system. It's primarily
used within the Yombo gateway to communication between libraries and modules. Libraries
and modules can subscribe to certain message types (commands, status) and receive
messages when activities take place.

Externally, messages are converted to various formats as required by the external
communication method. Libraries and modules that provide external communications must
convert from the Yombo Message to the form required by that commincation method. However,
care should be taken to convey as much of the message elements as practical.

Internally to the gateway software, the Yombo Message is responsible for
delivering commands and status updates to various libraries and modules for
further processing.

Other than a standard set of key components, the yombo message is fairly free
form. Module developers should follow these guidelines when developing modules
so that they can communicate with other modules. If additional standard fields
are needed, please start a new thread on the forums for discussion.

Additionally, 'product family types' such as X10, Insteon, Z-Wave, Audio, Video,
may have additional requirements.  See
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
import sys
from inspect import isfunction

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
        :param msgType: The type of message being sent, such as: command,
            event, status:

            * "cmd" - Used for sending commands to various devices. It is best
              to use Device library to complete this.
            * "voice_cmd" - Used by the voice_cmd module to send a registered
              voice_cmd to a module. This is used if the voice_cmd doesn't match
              a device_id.
            * "event" - Used to send various system events. # TODO: make a list!
            * "status" - Used for sending device status.  This is typically used
              by Device object to send status when something is changed.
        :type msgType: string
        :param msgStatus: **Required.** Status of this message (value depends
            on the msgType), such as - new, processing, done, failed, reply:

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
                     "device_id".

               * status message: Must include: 

                   * "device_id"
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
        :type sentTo: dict
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
               HTML5 clients, etc.  **Note**: If set, this must be set by the
               recieving library or module that has actually authenticated
               the user.
        :type msgAuth: dict
        :param newMessage: Default is True. Set to false to force simple
            validations on the message. For example, it will make sure the
            msgUUID exists and won't create a new one.
        :type newMessage: bool
        """
        self.loader = getLoader()
        self._MessagesLibrary = getComponent('yombo.gateway.lib.messages')
        self._ModulesLibrary = getComponent('yombo.gateway.lib.modules')

        self.msgOrigin      = kwargs['msgOrigin']
        self.msgDestination = kwargs['msgDestination']
        self.msgType        = kwargs['msgType']
        self.msgStatus      = kwargs['msgStatus']
        self.msgStatusExtra = kwargs.get('msgStatusExtra', None)
        self.textStatus     = kwargs.get('textStatus')
        self.uuidType       = kwargs.get('uuidType', 'z')
        self.uuidSubType    = kwargs.get('uuidSubType', 'z')
        self.msgUUID        = kwargs.get('msgUUID')
        self.msgOrigUUID    = kwargs.get('msgOrigUUID')
        self.payload        = kwargs['payload']
        self.msgAuth        = kwargs.get('msgAuth', {})
        self.msgPath        = OrderedDict([])
        kwargs['notBefore'] = kwargs.get('notBefore', 0)
        kwargs['maxDelay']  = kwargs.get('maxDelay', 0)
        kwargs['delay'] = kwargs.get('delay', 0)
        self.newMessage     = kwargs.get('newMessage', True)

        if 'msgPath' in kwargs:
            for hop in kwargs['msgPath']:
                self.msgPath[hop] = kwargs['msgPath'][hop]

        self.sentTo = []

        self.gwUUID = getConfigValue("core", "gwuuid")
        if self.msgUUID is None:
            if self.newMessage:
                self.msgUUID = str(generateUUID(mainType=self.uuidType, subType=self.uuidSubType))
            else:
                raise YomboMessageError("Existing message should have a msgUUID", 'Message API::Create message.')

        self.set_delay(**kwargs)

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

    def dumpToExternal(self, **kwargs):
        """
        Used to dump key parts of the message for an external source. Perfect for relaying complete messages
        to another gateway or 3rd party processor for advanced command & status processing.

        Ensures the message has full Origin and Destination routes.  Creates GPG signature and stores in msgAuth.
        """
        if self.validateMsgOriginFull() is False:
            YomboMessageError("Cannot dump message to external without full Origin path.")
        if self.validateMsgDestinationFull() is False:
            YomboMessageError("Cannot dump message to external without full Destination path.")

        newmsg = {
            'msgOrigin'     : str(self.msgOrigin),
            'msgDestination': str(self.msgDestination),
            'msgType'       : str(self.msgType),
            'msgStatus'     : str(self.msgStatus),
            'msgStatusExtra': str(self.msgStatusExtra),
            'msgUUID'       : str(self.msgUUID),
            'msgAuth'       : str(self.msgAuth),
            'msgOrigUUID'   : str(self.msgOrigUUID),
            'msgPath'       : str(self.msgPath),
            'payload'       : dict(self.payload),
            }

#TODO: Create signature method. :-)
#        self.generateMsgAuth()
        return newmsg


    def set_delay(self, **kwargs):
        """
        Used by get_message to set a delay. This is useful when a command to a device needs
        to be sent later.

        When these values are set, the messages are made persistent across restarts. It's
        advisable to set a 'notBefore'
        Used for controlling when to send a device command
        Sets a "not before" and "not after"
        To be documentated later. Basically, just sets notBefore and maxDelay
        based on kwargs.
        """
        notBefore = 0.0
        maxDelay = 0.0

        if 'notBefore' in kwargs:
            try:
              notBefore = float(kwargs['notBefore'])
              if notBefore > 0 and notBefore < time():
                raise YomboMessageError("Cannot set 'notBefore' to a time in the past.", errorno=150)
            except:
                raise YomboMessageError("notBefore is not an int or float.", errorno=151)
        elif 'delay' in kwargs:
            if kwargs['delay'] > 0:
                try:
                  notBefore = time() + float(kwargs['delay'])
                except:
                  raise YomboMessageError("delay is not an int or float", errorno=152)

        if 'maxDelay' in kwargs:
            if kwargs['maxDelay'] > 0:
                try:
                  maxDelay = float(kwargs['kwargs'])
                  if maxDelay < 0:
                    raise YomboMessageError("Max delay cannot be less then 0.", errorno=154)
                except:
                  raise YomboMessageError("maxDelay is not an int or float.", errorno=151)

        self.notBefore = notBefore
        self.maxDelay = maxDelay

    def validateMsgOriginFull(self):
        """
        Validates that the msgOrigin field has both sections path:id

        :return:
        """
        item = self.msgOrigin.split(":")
        if len(item) == 1:
            return False
        elif len(item) == 2:
            return True
        raise YomboMessageError("msgOrigin is in unknown state")

    def validateMsgDestinationFull(self):
        """
        Validates that the msgDestination field has both sections path:id

        :return:
        """
        item = self.msgDestination.split(":")
        if len(item) == 1:
            return False
        elif len(item) == 2:
            return True
        raise YomboMessageError("msgDestination is in unknown state")

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
        if self.validateMessage() is False:
            raise YomboMessageError("You should never see this message. If you do.  Please tell supprt@yombo.net about it!", 'Message API::Catchall')

        if self.checkDestinationAsLocal() is False:
            gc = getComponent('yombo.gateway.lib.gatewaycontrol')
            gc.message(self)
            logger.info("message is not marked for local. Sending to server for processing!")
            return
        if self.msgType == "control": # control messages
            if self.cmd == "disconnectSvc":
# TODO: finish this!
                pass
                self.loader.loadedComponents['yombo.gateway.lib.GatewayControlProtocol']

                
        if self._MessagesLibrary.processing is False:
            logger.debug("Message::send - Queuing message for later")
            self._MessagesLibrary.queue.appendleft(self)
            return

        # if message is to be delievered later, send to queue
        if self.notBefore > time.time():
            self._MessagesLibrary.add_msg_to_delay_queue(self)
            return

        # Now we are ready to send the message.  First tell messages library.
        self._MessagesLibrary.beforeSendMessage(self)

        #first send to target, then to distro lists
        destParts = self.msgDestination.split(".")
        allComponents = copy.copy(self.loader.loadedComponents)
        if self.msgDestination in allComponents:
            component = allComponents[self.msgDestination]
            if hasattr(component, 'message'):
#            if callable(component.message):
                self.sentTo.append(self.msgDestination)
                callLater(0.00001, component.message, self)
    #	            ret = component.message(self)                     # send actual message
            del allComponents[self.msgDestination]
        else:
            if destParts[2] != "all":
                logger.error("Send message: Invalid destination for message. Asked to send it to: {msgDestination}", msgDestination=self.msgDestination)
                # TODO: Perhaps send reponse to sender...security??
                return

        #second, send to distribution lists. If list exists, and not already sent.
        if self.msgType != "unknown":
            if self.msgType in self._MessagesLibrary.distributions:  # make sure dist exists
                for componentName in self._MessagesLibrary.distributions[self.msgType]:
                    if componentName in allComponents:   # make sure it's not already sent
                        component = allComponents[componentName]
                        callLater(0.00001, component.message, self)
                        self.sentTo.append(componentName)
                        del allComponents[componentName]  # remove, won't send again

        #third, send to distrubution "all" last.
        logger.debug("message - sending to all distro list: {distributions}", distributions=self._MessagesLibrary.distributions)
        if "all" in self._MessagesLibrary.distributions and (self.msgStatus == 'new' or self.msgType == 'event'):  # make sure dist exists
            for componentName in self._MessagesLibrary.distributions["all"]:
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
        logger.debug("MESAGE.update({updateDict})", updateDict=updateDict)
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
        is legitimate for the given device_id.

        Also checks valid device_id, etc.
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
#            return self.__validateEvent()

        # if origin isn't local, check for msgAuth and validate it.
        if self.checkOriginAsLocal() is False:
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
            raise YomboMessageError('msgDestination is missing or invalid. msgDestination: %s' % self.msgDestination,
                                    'Message API')
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
                    return False  # it's not even a gateway, so can't be us
            elif len(parts) == 2:
                if str(self.msgOrigin[:13]).lower() != "yombo.gateway" and parts[1] != self.gwUUID:
                    return False  # It's not us!
            else:
                raise YomboMessageError('msgOrigin is missing or invalid. msgOrigin: %s' % self.msgOrigin,
                                        'Message API')
        return True

    def __validateCmd(self):
        """
        Helper function for :py:func:`validateMessage` to validate command messages.
        """
        if self.msgStatus != 'new':
            return True
        
        logger.debug("validcmd payload: {payload}", payload=self.payload)

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

        # check device_id
        if 'deviceobj' in self.payload:
            if isinstance(self.payload['deviceobj'], Device):
                self.payload['device_id'] = self.payload['deviceobj'].device_id
                self.payload['device'] = self.payload['deviceobj'].label
            else:
                raise YomboMessageError("if 'deviceobj' specified', it must be a device instance.", 'Message API::ValidateCMD')
        elif 'device_id' in self.payload:
#            try:
#                logger.warn("aaaa1: {payload}", payload=self.payload)
                self.payload['deviceobj'] = getDevice(self.payload['device_id'])
#                logger.warn("aaaa2: {payload}", payload=self.payload)
                self.payload['device_id'] = self.payload['deviceobj'].device_id
#                logger.warn("aaaa3: {payload}", payload=self.payload)
                self.payload['device'] = self.payload['deviceobj'].label
#                logger.warn("aaaa4: {payload}", payload=self.payload)
 #           except:
 #               raise YomboMessageError("Couldn't find specified device_id. %s " % sys.exc_info()[0], 'Message API')
        elif 'device' in self.payload:
            try:
                self.payload['deviceobj'] = getDevice(self.payload['device'])
                self.payload['device_id'] = self.payload['deviceobj'].device_id
                self.payload['device'] = self.payload['deviceobj'].label
            except:
              raise YomboMessageError("Couldn't find specified device_id.", 'Message API')
        else:
            raise YomboMessageError("'device_id' or 'device' not found in payload. Required for commands.", 'Message API::ValidateCMD')

        logger.debug("available_commands: {available_commands}", available_commands=self.payload['deviceobj'].available_commands, )
        logger.debug("self.payload['{cmdobj}']", cmdobj=self.payload['cmdobj'])
        # check that command is possible for given device_id
        if self.payload['cmdobj'].cmdUUID not in self.payload['deviceobj'].available_commands:
           raise YomboMessageError("Invalid cmdUUID for this device_id.", 'Message API::ValidateCMD')

        # force delivery to the correct module.
        if(self.msgStatus == "new"):
#            logger.warn("what? {pay}", pay=self.payload['deviceobj'].dump())
            moduleLabel = "yombo.gateway.modules." + self._ModulesLibrary.get_device_routing(self.payload['deviceobj'].device_type_id, 'Command', 'moduleLabel').lower()
            if self.msgDestination != moduleLabel :
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

        hashed = {
            'msgOrigin'     : str(self.msgOrigin),
            'msgDestination': str(self.msgDestination),
            'msgType'       : str(self.msgType),
            'msgStatus'     : str(self.msgStatus),
            'msgStatusExtra': str(self.msgStatusExtra),
            'msgUUID'       : str(self.msgUUID),
            'msgAuth'       : str(self.msgAuth),
            'msgOrigUUID'   : str(self.msgOrigUUID),
            'msgPath'       : str(self.msgPath),
            'payload'       : dict(self.payload),
            }

        self.msgAuth['username'] = kwargs.get('username', '')
        self.msgAuth['signature'] = pgpSign(dumps(hashed))

    def validateMsgAuth(self):
        """
        Validates that the message authentication is valid.
        """
        if 'signature' in self.msgAuth:
            hashed = loads(pgpVerify(self.msgAuth['signature']))
            logger.debug("{hashed}", hashed=hashed)
            if self.msgOrigin != hashed['msgOrigin']:
                raise YomboMessageError("msgOrigin doesn't match hash.", 'Message API::ValidateMsgAuth')
            if self.msgDestination != hashed['msgDestination']:
                raise YomboMessageError("msgDestination doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgType) != hashed['msgType']:
                raise YomboMessageError("msgType doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgStatus) != hashed['msgStatus']:
                raise YomboMessageError("msgStatus doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgStatusExtra) != hashed['msgStatusExtra']:
                raise YomboMessageError("msgStatusExtra doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgUUID) != hashed['msgUUID']:
                raise YomboMessageError("msgUUID doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self.msgAuth['username']) != hashed['msgAuth']['username']:
                raise YomboMessageError("username doesn't match hash.", 'Message API::ValidateMsgAuth')
            if str(self._generatePayloadHash()) != hashed['payload']:
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
