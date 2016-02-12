# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Manages messages that are to be delivered at a later time (notBefore).
This library can take a message in, pickle it, and store it for persistency.

On startup, it checks the data store for delayed messages.  If one is found
it validates that notBefore has elapsed.  If it has, it then checks the
"maxDelay" of the message.  If the max delay has exceeded, a reply message
is generated with a status of "failed" and extended status of
"maxDelay reached".

Developers and users don't need to access anything here directly. A message
will delivery itself here automatically and this library will call the
send function of a message when needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import deque
import time

# Import twisted libraries
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboMessageError
#from yombo.core.helpers import getCommand, getDevice
from yombo.core.library import YomboLibrary
from yombo.core.message import Message
from yombo.core.sqldict import SQLDict  #load at the top of the file.
from yombo.core.log import getLogger
from yombo.utils import global_invoke_all

logger = getLogger('library.messages')

class Messages(YomboLibrary):
    """
    Store messages to be delivered in future here.
    """
    def _init_(self, loader):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self.loader = loader
        self.distributions = {}  # For message broadcasting lists.
        self.queue = deque()    # Placeholder for startup message queues
        self.processing = False

    def _load_(self):
        """
        Load the messages, but that's about it. Can't send any messages until start is reached. Can accept
        messages by the time load has completed.
        """
        self.delayQueue = SQLDict(self, "messages") # lets use sqldict to do the heavy lifting
        self.reactors = {} # map msgUUID to a reactor (delayed message)
        self.deviceList = {} # list of devices that have pending messages.

    def _start_(self):
        """
        Nothing to do here, wait for modules started.
        """
        pass

    def _stop_(self):
        """
        Stop library - stop the looping call.
        """
        pass

    def _unload_(self):
        pass

    def _module_prestart_(self, **kwargs):
        """
        Called after _load_ is called for all the modules. Return a simple list of messages to subscribe to.

        **Usage**:

        .. code-block:: python

           def ModuleName_message_subscriptions(self, **kwargs):
               return ['status']
        """
        subscriptions_to_add = global_invoke_all('message_subscriptions')
#        logger.debug("subscriptionstoadd: {subToAdd}", subToAdd=subscriptions_to_add)

        for component, subscriptions in subscriptions_to_add.iteritems():
            if subscriptions is None:
                continue
            for list in subscriptions:
                logger.debug("For module {component}, adding distro: {list}", component=component, list=list)
                self.updateSubscription("add", list, component)

    def _module_started_(self):
        """
        On start, sends all queued messages. Then, check delayed messages
        for any messages that were missed. Send old messages
        and prepare future messages to run.
        """
        self.processing = True
        while len(self.queue) > 0:
            m = self.queue.pop()
            try:
                m.send()
            except YomboMessageError:
                pass

        # Now check to existing delayed messages.  If not too old, send
        # otherwise delete them.  If time is in future, setup a new
        # reactor to send in future.
        for msg in self.delayQueue:
          if float(msg.notBefore) < time.time():
              if time.time() - float(msg.notBefore) > float(msg.maxDelay):
                  # we're too late, just delete it.
                  del self.delayQueue[msg]
                  continue
              else:
                #we're good, lets hydrate the message and send it.
                toSend = Message(**self.delayQueue[msg])
                del self.delayQueue[msg]
                toSend.send()
          else: # now lets setup messages for the future. Gotta wear shades.

              self.reactors[msg] = reactor.callLater(2, self.loaded)
              #Hydrate the message and prep it to send.
              toSend = Message(**self.delayQueue[msg])
              when = float(msg.notBefore) - time.time()
              reactor.callLater(when, toSend.send)

    def _module_unload_(self):
        """
        Used by the loader module to clear all library and module subscriptions.
        """
        logger.warn("Message - _module_unload_....!")
        if hasattr(self, 'distributions'): # used incase GW stops premature.
            self.distributions.clear()

    def addToDelay(self, message):
        """
        Add a message to the delay queue be delivered at 'notBefore' time.

        :param message: The message to be added for later delivery.
        :type message: message object
        """
        temp = message.dump()
        if 'commandobj' in temp['payload']:
          temp['payload']['cmdUUID'] = temp['payload']['commandobj'].cmdUUID
          del temp['payload']['commandobj']
        if 'deviceobj' in temp['payload']:
          temp['payload']['device_id'] = temp['payload']['deviceobj'].device_id
          del temp['payload']['deviceobj']

        when = time.time() - message.notBefore
        self.reactors = reactor.callLater(when, message.send)

        if temp['payload']['device_id'] not in self.deviceList:
          self.deviceList[temp['payload']['device_id']] = []
        self.deviceList.append(message.msgUUID)

        self.delayQueue[message.msgUUID] = temp  # dehydrate for persistence
        reply = message.getReply(msgStatus="delayed")
        reply.send()

    def deviceDelayCancel(self, device_id):
        """
        Cancel any pending messages for a given device_id.
        :param device_id: The msgUUID to be removed.
        :type device_id: string
        """

        if device_id in self.deviceList:
          for key in range(len(self.deviceList[device_id])):
              try:
                self.cancelDelay(self.deviceList[device_id][key])
              except:
                pass
              del self.deviceList[device_id][key]
        del self.deviceList[device_id]

    def deviceDelayList(self, device_id):
        """
        Return a list of messageUUID's for delayed messages for a given device_id.
        :param device_id: The msgUUID to be removed.
        :type device_id: string
        """
        if device_id in self.deviceList:
          return self.deviceList[device_id]

    def cancelDelay(self, msgUUID):
        """
        Remove a message from being delayed.

        :param msgUUID: The msgUUID to be removed.
        :type msgUUID: string
        """
        isGood = True
        if msgUUID in self.reactors:
          if callable(self.reactors[msgUUID].cancel):
            if self.reactors[msgUUID].active():
                self.reactors[msgUUID].cancel()
            del self.reactors[msgUUID]
        else:
            isGood = False
        if msgUUID in self.delayQueue:
            del self.delayQueue[msgUUID]
        else:
            raise YomboMessageError("msgUUID not found in delay queue.", 'Messages Library')

        if isGood is False:
            raise YomboMessageError("msgUUID not found in reactors.", 'Messages Library')

    def checkDelay(self, msgUUID):
        """
        Check if a message is in the delay queue.
        :param msgUUID: The msgUUID to check.
        :type msgUUID: string
        """
        return msgUUID in self.delayQueue

    def beforeSendMessage(self, message):
        """
        This is called by the message instance to let us know it's going to
        send itself now.  We'll use this later to capture stats, sent to hooks, etc.
        We will check if the message is in the delayQueue, if it is, we'll
        delete that and clean up the reactors list.
        """
        try:
          self.cancelDelay(message.msgUUID)
        except:
          pass

    def message(self, message):
        """
        To be completed. Will return a list of pending messages.
        """
        if message.msgDestination.lower() != self._FullName.lower():
            return  #we don't care about other people for now.

        # not completed.

    def updateSubscription(self, action, list, moduleName):
        """
        Used by the loader module to add or remove a moduleName to a given list.

        :param action: Either add or remove.
        :type action: string
        :param list: The name of the list to add moduleName too.
        :type list: string
        :param moduleName: The name of the module to add to a list.
        :type moduleName: string
        """
        moduleName = moduleName.lower()
        if list not in self.distributions:
            self.distributions[list] = []

        if action == "add":
            if moduleName not in self.distributions[list]:
                self.distributions[list].append(moduleName)
        elif action == "remove":
            try:
                self.distributions[list].remove(moduleName)
            except:
                pass

