# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Setups up various times.  Also creates events for next sunrise/sunset, etc.

This module can be used to get various times of various objects
in the sky.

See usage below on using this module within your module.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getTimes
       times = getTimes()
       moonrise = times.objRise(1, 'Moon') # 1 - we want the next moon rise

       # The following can be used in logic for day/night/light/dark events.
       #times.isTwilight = True - it's not dark (sundown) or light (sun up), or False if not.
       #times.isLight = True - Its either twilight or sun up - False - it's really dark!
       #times.isDark = Opposite of isLight
       #times.isDay = True - sunup, False - sun below twilightHorizon (-6 degrees)
       #times.isNight = Opposite of isDay
       #times.isDawn = True - Is twilight in the morning, else false.
       #times.isDusk = True - Is twilight at night, else false.

.. todo::
  Redo many parts of this module. Doesn't seem to be working.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

import ephem
from time import time
from calendar import timegm as CalTimegm
from datetime import datetime, date, timedelta

from twisted.internet import reactor

from yombo.core.exceptions import TimeError
from yombo.core.helpers import getConfigValue
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.message import Message

logger = getLogger('library.times')

class Times(YomboLibrary):
    """
    Provide various rise/set of the sun, moon, and all things heavenly.
    """
    def init(self, loader):
        """
        Setup various common objects, setup frame work if isday/night/dark/twilight.
        :param loader: A pointer to the L{Loader<yombo.lib.loader.Loader>}
        library.
        :type loader: Instance of Loader
        """
        self.loader = loader

        self.obs = ephem.Observer()
        self.obs.lat = str(getConfigValue('location', 'latitude', 0))
        self.obs.long = str(getConfigValue('location', 'longitude', 0))
        self.obs.elevation = int(getConfigValue('location', 'elevation', 800))

        self.obsTwilight = ephem.Observer()
        self.obsTwilight.horizon = str(getConfigValue('times', 'twilightHorizon', '-6')) # civil = -6, nautical = -12, astronomical = -18
        self.obsTwilight.lat = str(getConfigValue('location', 'latitude', 0))
        self.obsTwilight.long = str(getConfigValue('location', 'longitude', 0))
        self.obsTwilight.elevation = int(getConfigValue('location', 'elevation', 800))

        self.isTwilight = None
        self.isLight = None
        self.isDark = None        
        self.isDay = None
        self.isNight = None
        self.isDawn = None
        self.isDusk = None

        self.CLnowLight = None
        self.CLnowDark = None
        self.CLnowDay = None
        self.CLnowNight = None
        
        self.CLnowNotDawn = None
        self.CLnowNotDusk = None
        self.CLnowDawn = None
        self.CLnowDusk = None

        self._setupLightDarkEvents()
        self._setupDayNightEvents()
        self._setupTwilightEvents() # needs to be called before setupNextDawnDuskEvent
        self._setupNextDawnDuskEvent()
        
    def load(self):
        """
        Already done, nothing to do.
        """
        pass

    def start(self):
        """
        Already done, nothing to do.
        """
        pass

    def _setupLightDarkEvents(self):
        """
        Setup events to be called when isLight and isDark needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
       
        This is different than day/night since it accounts for twilight.
        """
        self._CalcLightDark() # setup isLight & isDark
        logger.info("islight: %s", self.isLight)

        setTime = 0
        if self.isLight:
            setTime = time() - self.sunSetTwilight() 
            print "%d = %d - %d" % (setTime, time(), self.sunSetTwilight())
            self.CLnowDark = reactor.callLater(setTime, self.sendStatus, 'nowDark')
            print "self.CLnowDark = reactor.callLater(setTime, self.sendStatus, 'nowDark')"
        else:
            setTime = time() - self.sunRiseTwilight()
            print "setTime = time() - self.sunRiseTwilight()"
            print "%d = %d - %d" % (setTime, time(), self.sunRiseTwilight())
            self.CLnowLight = reactor.callLater(setTime, self.sendStatus, 'nowLight')

        #set a callLater to redo islight/dark, and setup next broadcast.
        reactor.callLater(setTime - 0.1, self._setupLightDarkEvents)


    def _setupDayNightEvents(self):
        """
        Setup events to be called when isDay and isNight needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
       
        This is different than light/dark since this doesn't account
        for twilight.
        """
        self._CalcDayNight()
        if self.isDay:
            setTime = time() - self.sunSet() + 0.01
            logger.trace("NowNight3 event in: %s", setTime)
            self.CLnowNight = reactor.callLater(setTime, self.sendStatus, 'nowNight')
        else:
            setTime = time() - self.sunRise() + 0.01
            logger.trace("NowDay4 event in: %s", setTime)
            self.CLnowDay = reactor.callLater(setTime, self.sendStatus, 'nowDay')

        #set a callLater to redo isday/night, and setup next broadcast.
        reactor.callLater(setTime- 0.1, self._setupDayNightEvents)

    ###  This function is not complete.  Need to calculate when the next
    ###  twilight period is. I just copied setupDayNightEvents to here for now.
    # When fixed, remove self._CalcTwilight() from def _setupNextDawnDuskEvent
    
    def _setupTwilightEvents(self):
        """
        Setup events to be called when isTwilight needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
       
        This is different than light/dark since this doesn't account
        for twilight.
        """
        pass  ## we are out of service for now..
        self._CalcTwilight()  #is it twilight right now?

        if self.isTwilight:
            setTime = time() - self.sunSet() + 0.01
            logger.trace("NowNight3 event in: %s", setTime)
            self.CLnowNight = reactor.callLater(setTime, self.sendStatus, 'nowNight')
        else:
            setTime = time() - self.sunRise() + 0.01
            logger.trace("NowDay4 event in: %s", setTime)
            self.CLnowDay = reactor.callLater(setTime, self.sendStatus, 'nowDay')

        #set a callLater to redo isday/night, and setup next broadcast.
        reactor.callLater(setTime- 0.1, self._setupDayNightEvents)


    def _setupNextDawnDuskEvent(self):
        """
        Setup events to be called when it's either dawn, notdawn, dusk,
        and notdusk.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
        """
        self.CLnowNotDawn = None
        self.CLnowNotDusk = None
        self.CLnowDawn = None
        self.CLnowDusk = None
        
        self._CalcTwilight()  #is it twilight right now?
        
        sunrise = self.sunRise() # for today
        sunset = self.sunSet()  # for today
        logger.debug("_setupNextDawnDuskEvent ------------------------ %s --", sunset)
        curtime = time()
            
        # First, determine we are closer to sunrise or sunset
        secsRise = abs(sunrise - curtime)
        secsSet = abs(sunset - curtime)
        
        twilightTimes = self.nextTwilight()
        startTime = twilightTimes['start'] - time()  # Will be now if it is twilight already.
        endTime = twilightTimes['end'] - time() + 0.01 # a partial second so we don't sent multiple events

        if self.isTwilight == True:
            if secsRise > secsSet: #  it's dawn right now = twilight + closer to sunrise
                self.CLnowNotDawn = reactor.callLater(endTime, self._sendNowNotDawn) # set a timer for no more dawn
            else: # else, closer to sunset.
                self.CLnowNotDusk = reactor.callLater(endTime, self._sendNowNotDusk) # set a timer for no more dusk
        else: # it's not twilight, we need to set a time for it to start.
            if secsRise > secsSet: #  it's going to be dawn next = no twilight + closer to sunrise
                self.CLnowDawn = reactor.callLater(endTime, self._sendNowDawn) # set a timer for is dawn
            else: # else, we are closer to sunset!
                self.CLnowDusk = reactor.callLater(endTime, self._sendNowDusk) # set a timer for is dusk
        
        logger.trace("Start/stop dawn in: %s / %s", startTime, endTime)

    def _sendNowDawn(self):
        """
        Called by timer when it's nowDawn.
        """
        self.isDawn = True
        self.sendStatus('nowDawn')
        self._setupNextTwlightEvents()
        
    def _sendNowNotDawn(self):
        """
        Called by timer when it's nowNotDawn. Calls _setupNextTwlightEvents
        to setup the next twilight cycle for dusk.
        """
        self.isDawn = False
        self.sendStatus('nowNotDawn')
        self._setupNextTwlightEvents()

    def _sendNowDusk(self):
        """
        Called by timer when it's nowDusk.
        """
        self.isDusk = True
        self.sendStatus('nowDusk')
        self._setupNextTwlightEvents()
        
    def _sendNowNotDusk(self):
        """
        Called by timer when it's nowNotDusk. Calles _setupNextTwlightEvents
        to setup the next twilight cycle for dawn.
        """
        self.isDusk = False
        self.sendStatus('nowNotDusk')
        self._setupNextTwlightEvents()
        
    def sendStatus(self, msgstatus):
        """
        Generate an "event" message of status type being the time
        event name.
        """
        msg = {
               'msgOrigin'      : self._FullName,
               'msgDestination' : "yombo.gateway.all",
               'msgType'        : 'event', 
               'msgStatus'      : msgstatus,
               'uuidType'       : "0",
               'uuidSubType'    : "040",
               'payload'        : {},
               }
        logger.debug("Time event: %s", msg)
        message = Message(**msg)
        message.send()

# To be removed, maybe.. -- Mitch
#    def _isDawn(self):
#        """
#        Sets the class variable "isDawn". This is called on gateway startup
#        and whenever the an is dawn event occurs.
#        """
#        self.obs.date = datetime.utcnow()
#        self.obsTwilight.date = datetime.utcnow()
#        timenow = datetime.utcnow()
#        logger.debug("timenow = %d", timenow)
#        if self.obsTwilight.next_rising(ephem.Sun()).datetime() < timenow < self.obs.next_rising(ephem.Sun()).datetime():
#            self.isDawn = True
#        else:
#            self.isDawn = False
#
#    def _isDusk(self):
#        """
#        Returns true it's twilight & dusk
#        """
#        self.obs.date = datetime.utcnow()
#        self.obsTwilight.date = datetime.utcnow()
#        timenow = datetime.utcnow()
#        logger.debug("timenow = %d", timenow)
#        if self.obs.next_setting(ephem.Sun()).datetime() < timenow < self.obsTwilight.next_setting(ephem.Sun()).datetime():
#            self.isDusk = True
#        else:
#            self.isDusk = False
#
    def _CalcTwilight(self):
        """
        Sets the class variable "isTwilight" depending if it's
        twilight right now. This is called everytime gateway starts
        and when the last twilight has ended.
        """
        self.obs.date = datetime.utcnow()
        self.obsTwilight.date = datetime.utcnow()
        timenow = datetime.utcnow()

        if self.obsTwilight.next_rising(ephem.Sun()).datetime() < timenow < self.obs.next_rising(ephem.Sun()).datetime() or \
          self.obs.next_setting(ephem.Sun()).datetime() < timenow < self.obsTwilight.next_setting(ephem.Sun()).datetime():
            self.isTwilight = True
        else:
            self.isTwilight = False
        print "istwilight = %s" % self.isTwilight

    def _CalcLightDark(self):
        """
        Sets the isLight and isDark vars.  It's light if the sun is up and it's twilight.
        """
        self.obs.date = datetime.utcnow()
        self.obsTwilight.date = datetime.utcnow()
        logger.info("isLight: %s < %s", self.obsTwilight.previous_rising(ephem.Sun()), self.obsTwilight.previous_setting(ephem.Sun()))

        if self.obsTwilight.previous_rising(ephem.Sun()) < self.obsTwilight.previous_setting(ephem.Sun()):
            self.isLight = True
            self.isDark = False
        else:
            self.isLight = False
            self.isDark = True

    def _CalcDayNight(self):
        """
        Sets up isDay and isNight. Is day if the sun is not below horizon.
        """
        self.obs.date = self.obsTwilight.date = datetime.utcnow()
        if ephem.localtime(self.obs.previous_rising(ephem.Sun())) <  datetime.now() < ephem.localtime(self.obs.next_setting(ephem.Sun())):
            self.isDay = False
            self.isNight = True
        else:
            self.isDay = True
            self.isNight = False

    def nextTwilight(self):
        """
        Returns the times of the next twilight. If it's currently twilight, then start will be "0".
        """
        self.obs.date = datetime.utcnow()
        self.obsTwilight.date = datetime.utcnow()
        if self.isDay:
            start = self.obsTwilight.next_setting(ephem.Sun())
            end = self.obs.next_setting(ephem.Sun())
        else:
            start = self.obsTwilight.next_rising(ephem.Sun())
            end = self.obs.next_rising(ephem.Sun())
        if  self.isTwilight == True:
            start = 0
        return {'start' : int(CalTimegm( start.tuple()) ), 'end' : int(CalTimegm( end.tuple() ))}

    def objVisible(self, object):
        """
        Returns a true if the given object is above the horizon.

        **Usage**:
        
        .. code-block:: python
          
            from yombo.core.helpers import getTime
            time = getTime()
            saturnVisible = getTime('Saturn') # Is Saturn above the horizon? (True/False)
        """
        try:
            obj = getattr(ephem, object)
        except AttributeError:
            raise TimeError("Couldn't not find PyEphem object: %s" % object)
            
        self.obs.date = datetime.utcnow()
        if ephem.localtime(self.obs.previous_rising(obj)) <  datetime.now() < ephem.localtime(self.obs.next_setting(obj)):
            return False
        else:
            return True

            
    def objRise(self, dayOffset, object):
        """
        Returns when an item/object rises or sets.
        
        **Usage**:
        
        .. code-block:: python
          
            from yombo.core.helpers import getTime
            time = getTime()
            saturnRise = getTime(1, 'Saturn') # the NEXT (1) rising of Saturn.
        """

        try:
            obj = getattr(ephem, object)
        except AttributeError:
            raise TimeError("Couldn't not find PyEphem object: %s" % object)
            
        self.obs.date = date.today()+timedelta(days=dayOffset)
        temp = self.obs.next_rising(obj())
        return int( CalTimegm( temp.tuple() ) )
    
    def objSet(self, dayOffset=0, object="Sun"):
        """
        Returns the setting time for a given object name, such as "Sun", "Moon". Optionaly returns sunset +/- # days.

        :param dayOffset: How many days to offset. 0 is today, 1 would be next, -1 is yesterday.
        :type dayOffset: int
        :param object: Which object to return information on. Sun, Moon, Mars, Jupiter, etc.
        :type object: string
        """
        try:
            obj = getattr(ephem, object)
        except AttributeError:
            obj = getattr(ephem, 'Sun')

        # we want the date part only, but date.today() isn't UTC.
        dt = datetime.utcnow()+timedelta(days=dayOffset)
        dt.replace(hour=0)
        dt.replace(minute=0)
        dt.replace(second=1)
        self.obs.date = dt
        temp = self.obs.next_setting(obj())
        return int( CalTimegm( temp.tuple() ) )

    def sunRise(self, dayOffset=1):
        """
        Return sunrise, optionaly returns sunrise +/- # days. The offset of "1" would be
        for the next sunrise.
        
        :param dayOffset: How many days to offset. 0 is today, 1 would be next, -1 is yesterday.
        :type dayOffset: int
        :param object: Which object to return information on. Sun, Moon, Mars, Jupiter, etc.
        :type object: string
        """
        return self.objRise(dayOffset, 'Sun')

    def sunSet(self, dayOffset=0, object='Sun'):
        """
        Return sunset, optionaly returns sunset +/- # days.

        :param dayOffset: How many days to offset. 0 is today, 1 would be next, -1 is yesterday.
        :type dayOffset: int
        :param object: Which object to return information on. Sun, Moon, Mars, Jupiter, etc.
        :type object: string
        """
        return self.objSet(dayOffset, object)


    def sunRiseTwilight(self, dayOffset=1, object='Sun'):
        """
        Return sunrise, optionaly returns sunrise +/- # days.
        """
        try:
            obj = getattr(ephem, object)
        except AttributeError:
            obj = getattr(ephem, 'Sun')
            
        self.obsTwilight.date = date.today()+timedelta(days=dayOffset)
        temp = self.obsTwilight.next_rising(obj())
        return int( CalTimegm(temp.tuple()) )

    def sunSetTwilight(self, dayOffset=0, object='Sun'):
        """
        Return sunset, optionaly returns sunset +/- # days.
        """
        try:
            obj = getattr(ephem, object)
        except AttributeError:
            obj = getattr(ephem, 'Sun')

        # we want the date part only, but date.today() isn't UTC.
        dt = datetime.utcnow()+timedelta(days=dayOffset)
        dt.replace(hour=0)
        dt.replace(minute=0)
        dt.replace(second=1)
        self.obsTwilight.date = dt
        temp = self.obsTwilight.next_setting(obj())
        return int( CalTimegm(temp.tuple()) )

