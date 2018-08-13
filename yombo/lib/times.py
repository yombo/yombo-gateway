# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Times @ Module Development <https://yombo.net/docs/libraries/times>`_


Sets up various times and events for: dusk, dawn, sunrise, sunset. Also send event messages when a status change
changes.  It also configures many State items such as times_light, times_dark, times_dawn, times_dusk

This library uses the python Ephem module to provide many astronomy computations, such as which objects are
above or below the horizon (saturn, moon, sun, etc), and then they will transition next.

**Usage**:

.. code-block:: python

   times = self._Libraries['Times']
   moonrise = times.item_rise(dayOffset=1, item='Moon') # 1 - we want the next moon rise


.. todo::

  Polar region debug (some strange glitches like nowNight message when it is polar day (I think we need variables for
  polar day and night begin/end)


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>


:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/times.html>`_
"""
# Import python libraries
from calendar import timegm as CalTimegm
from datetime import datetime, timedelta
import ephem

import time
from typing import Any
import pytz

# Import twisted libraries
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import InvalidArgumentError, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import is_one_zero, global_invoke_all
import yombo.utils.datetime as dt


logger = get_logger('library.times')

class Times(YomboLibrary, object):
    """
    Provides light/dark/dusk/dawn status, times, and events. Also provides various rise/set of the sun, moon, and all
    things heavenly.
    """

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo times library"

    def _init_(self, PatchEnvironment = False):
        """
        Setup various common objects, setup frame work if isday/night/dark/twilight.
        :param loader: A pointer to the L{Loader<yombo.lib.loader.Loader>}
        library.
        :type loader: Instance of Loader
        """
        if PatchEnvironment:
            self.runned_for_tests()

        self.setup_obs()

        self.is_now_init = True
        self._setup_light_dark_events()
        self._setup_day_night_events()  # includes next sunrise, sunset, is sun visable, etc.
        self._setup_next_twilight_events() # needs to be called before setupNextDawnDuskEvent
        self._setup_next_dawn_dusk_event()
        self._setup_moon_events()
        self._setup_weekday_events()
        self.is_now_init = False

    def setup_obs(self):
        self.obs = ephem.Observer()
        self.obs.lat = str(self._Configs.get('location', 'latitude', 38.576694))
        self.obs.lon = str(self._Configs.get('location', 'longitude', -121.493259))
        self.obs.elevation = int(self._Configs.get('location', 'elevation', 800))

        self.obsTwilight = ephem.Observer()
        # civil = -6, nautical = -12, astronomical = -18
        self.obsTwilight.horizon = str(self._Configs.get('times', 'twilighthorizon', '-6'))
        self.obsTwilight.lat = str(self._Configs.get('location', 'latitude', 38.576694))
        self.obsTwilight.lon = str(self._Configs.get('location', 'longitude', -121.493259))
        self.obsTwilight.elevation = int(self._Configs.get('location', 'elevation', 800))

    @property
    def next_new_moon(self):
        return self._timegm(ephem.next_new_moon(datetime.now()))

    @property
    def next_first_quarter_moon(self):
        return self._timegm(ephem.next_first_quarter_moon(datetime.now()))

    @property
    def next_full_moon(self):
        return self._timegm(ephem.next_full_moon(datetime.now()))

    @property
    def next_last_quarter_moon(self):
        return self._timegm(ephem.next_last_quarter_moon(datetime.now()))

    @property
    def is_moon_visible(self):
        return self.__is_moon_visible

    @property
    def moon_info(self):
        self.obs.date = datetime.utcnow()
        moon = ephem.Moon()
        moon.compute(self.obs)
        return {
            'phase': moon.phase,
            'az': str(moon.az),
            'alt': str(moon.alt),
        }

    @property
    def sun_info(self):
        self.obs.date = datetime.utcnow()
        sun = ephem.Sun()
        sun.compute(self.obs)
        return {
            'az': str(sun.az),
            'alt': str(sun.alt),
        }

    @is_moon_visible.setter
    def is_moon_visible(self, val):
        self._States.set('is.moonvisible', val, 'bool')
        self.__is_moon_visible = val
        self._Statistics.datapoint("lib.times.is_moonvisible", is_one_zero(val))

    @property
    def is_sun_visible(self):
        return self.__is_sun_visible

    @is_sun_visible.setter
    def is_sun_visible(self, val):
        self._States.set('is.sunvisible', val, 'bool')
        self.__is_sun_visible = val
        # print("is sun visable: %s" % val)
        self._Statistics.datapoint("lib.times.is_sunvisible", is_one_zero(val))

    @property
    def is_twilight(self):
        return self.__is_twilight

    @is_twilight.setter
    def is_twilight(self, val):
        self._States.set('is.twilight', val, 'bool')
        self.__is_twilight = val
        self._Statistics.datapoint("lib.times.is_twilight", is_one_zero(val))

    @property
    def is_twilight(self):
        return self.__is_twilight

    @is_twilight.setter
    def is_twilight(self, val):
        self._States.set('is.twilight', val, 'bool')
        self.__is_twilight = val
        self._Statistics.datapoint("lib.times.is_twilight", is_one_zero(val))

    @property
    def is_light(self):
        return self.__is_light

    @is_light.setter
    def is_light(self, val):
        self._States.set('is.light', val, 'bool')
        self.__is_light = val
        self._Statistics.datapoint("lib.times.is_light", is_one_zero(val))

    @property
    def is_dark(self):
        return self.__is_dark

    @is_dark.setter
    def is_dark(self, val):
        self._States.set('is.dark', val, 'bool')
        self.__is_dark = val
        self._Statistics.datapoint("lib.times.is_dark", is_one_zero(val))

    @property
    def is_day(self):
        return self.__is_day

    @is_day.setter
    def is_day(self, val):
        self._States.set('is.day', val, 'bool')
        self.__is_day = val
        self._Statistics.datapoint("lib.times.is_day", is_one_zero(val))

    @property
    def is_night(self):
        return self.__is_night

    @is_night.setter
    def is_night(self, val):
        self._States.set('is.night', val, 'bool')
        self.__is_night = val
        self._Statistics.datapoint("lib.times.is_night", is_one_zero(val))

    @property
    def is_dawn(self):
        return self.__is_dawn

    @is_dawn.setter
    def is_dawn(self, val):
        self._States.set('is.dawn', val, 'bool')
        self.__is_dawn = val
        self._Statistics.datapoint("lib.times.is_dawn", is_one_zero(val))

    @property
    def is_dusk(self):
        return self.__is_dusk

    @is_dusk.setter
    def is_dusk(self, val):
        self._States.set('is.dusk', val, 'bool')
        self.__is_dusk = val
        self._Statistics.datapoint("lib.times.is_dusk", is_one_zero(val))

    @property
    def is_weekend(self):
        return self.__is_weekend

    @is_weekend.setter
    def is_weekend(self, val):
        self._States.set('is.weekend', val, 'bool')
        self.__is_weekend = val

    @property
    def is_weekday(self):
        return self.__is_weekday

    @is_weekday.setter
    def is_weekday(self, val):
        self._States.set('is.weekday', val, 'bool')
        self.__is_weekday = val

    @property
    def day_of_week(self):
        return self.__day_of_week

    @day_of_week.setter
    def day_of_week(self, val):
        self._States.set('day_of_week', val, 'string')
        self.__day_of_week = val

    @property
    def next_day(self):
        return self.__next_day

    @next_day.setter
    def next_day(self, val):
        if '__next_day' in locals():
            if val != self.__next_day:
                self._States.set('next.day', int(round(val)), 'epoch')
                self.__next_day = val
        else:
            self.__next_day = val
            self._States.set('next.day', int(round(val)), 'epoch')

    @property
    def next_night(self):
        return self.__next_night

    @next_night.setter
    def next_night(self, val):
        if '__next_night' in locals():
            if val != self.__next_night:
                self._States.set('next.night', int(round(val)), 'epoch')
                self.__next_night = val
        else:
            self.__next_night = val
            self._States.set('next.night', int(round(val)), 'epoch')

    @property
    def next_light(self):
        return self.__next_light

    @next_light.setter
    def next_light(self, val):
        if '__next_light' in locals():
            if val != self.__next_light:
                self._States.set('next.light', int(round(val)), 'epoch')
                self.__next_light = val
        else:
            self.__next_light = val
            self._States.set('next.light', int(round(val)), 'epoch')

    @property
    def next_dark(self):
        return self.__next_day

    @next_dark.setter
    def next_dark(self, val):
        if '__next_dark' in locals():
            if val != self.__next_dark:
                self._States.set('next.dark', int(round(val)), 'epoch')
                self.__next_dark = val
        else:
            self.__next_dark = val
            self._States.set('next.dark', int(round(val)), 'epoch')

    @property
    def next_wilight_start(self):
        return self.__next_wilight_start

    @next_wilight_start.setter
    def next_wilight_start(self, val):
        if '__next_wilight_start' in locals():
            if val != self.__next_wilight_start:
                self._States.set('next.twilightstart', int(round(val)), 'epoch')
                self.__next_wilight_start = val
        else:
            self.__next_wilight_start = val
            self._States.set('next.twilightstart', int(round(val)), 'epoch')

    @property
    def next_twilight_end(self):
        return self.__next_twilight_end

    @next_twilight_end.setter
    def next_twilight_end(self, val):
        if '__next_twilight_end' in locals():
            if val != self.__next_twilight_end:
                self._States.set('next.twilightend', int(round(val)), 'epoch')
                self.__next_twilight_end = val
        else:
            self.__next_twilight_end = val
            self._States.set('next.twilightend', int(round(val)), 'epoch')

    @property
    def next_sunrise(self):
        return self.__next_sunrise

    @next_sunrise.setter
    def next_sunrise(self, val):
        if '__next_sunrise' in locals():
            if val != self.__next_sunrise:
                self._States.set('next.sunrise', int(round(val)), 'epoch')
                self.__next_sunrise = val
        else:
            self.__next_sunrise = val
            self._States.set('next.sunrise', int(round(val)), 'epoch')

    @property
    def next_sunset(self, val):
        return self.__next_sunset

    @next_sunset.setter
    def next_sunset(self, val):
        if '__next_sunset' in locals():
            if val != self.__next_sunset:
                self._States.set('next.sunset', int(round(val)), 'epoch')
                self.__next_sunset = val
        else:
            self._States.set('next.sunset', int(round(val)), 'epoch')
            self.__next_sunset = val

    @property
    def next_moonrise(self):
        return self.__moonRise

    @next_moonrise.setter
    def next_moonrise(self, val):
        if '__moonRise' in locals():
            if val != self.__moonRise:
                self._States.set('next.moonrise', int(round(val)), 'epoch')
                self.__moonRise = val
        else:
            self._States.set('next.moonrise', int(round(val)), 'epoch')
            self.__moonRise = val

    @property
    def next_moonset(self):
        return self.__moonSet

    @next_moonset.setter
    def next_moonset(self, val):
        if '__moonSet' in locals():
            if val != self.__moonSet:
                self._States.set('next.moonset', int(round(val)), 'epoch')
                self.__moonSet = val
        else:
            self._States.set('next.moonset', int(round(val)), 'epoch')
            self.__moonSet = val

    # Functions dealing with celestial objects

    def twilight_times(self):
        """
        Returns a dictionary containing the next time twilight starts and ends.
        """
        if self.is_dark:
            type = 'sunrise'
        else:
            type = 'sunset'
        return {'start': self.next_wilight_start, 'end': self.next_twilight_end, 'now': self.is_twilight, 'type': type}

    def item_visible(self, **kwargs):
        """
        Returns a true if the given item is above the horizon.

        **Usage**:

        .. code-block:: python

            saturn_visible = self._Times.item_visible(item='Saturn') # Is Saturn above the horizon? (True/False)

        :raises InvalidArgumentError: Raised if an argument is invalid or illegal.
        :raises AttributeError: Raised if PhPhem doesn't have the requested item.
        :param item: The device UUID or device label to search for.
        :type item: string
        :return: Pointer to array of all devices for requested device type
        :rtype: dict
        """
        if 'item' not in kwargs:
            raise InvalidArgumentError("Missing 'item' argument.")
        item = kwargs['item']

        try:
            obj = getattr(ephem, item)
        except AttributeError:
            raise AttributeError("PyEphem doesn't have requested item: %s" % item)
        self.obs.date = datetime.utcnow()

        # if it is rised and not set, then it is visible
        # print("item_visiable: %s" % item)
        # print("self._previous_rising(self.obs, obj()): %s" % self._timegm(self._previous_rising(self.obs, obj())))
        # print("self._previous_setting(self.obs, obj()): %s" % self._timegm(self._previous_setting(self.obs, obj())))
        if self._timegm(self._previous_rising(self.obs, obj())) < self._timegm(self._previous_setting(self.obs, obj())):
            # print("nope")
            return False
        else:
            # print("yeap")
            return True

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def item_rise(self, **kwargs):
        """
        Returns when an item rises.

        **Usage**:

        .. code-block:: python

            mars_rise = self._Times.item_rise(dayOffset=1, item='Saturn') # the NEXT (1) rising of Mars.

        :raises InvalidArgumentError: Raised if an argument is invalid or illegal.
        :raises AttributeError: Raised if PhPhem doesn't have the requested item.
        :param dayOffset: Default=0. How many days in future to find when item rises. 0 = Today, 1=Tomorrow, etc, -1=Yesterday
        :type dayOffset: int
        :param item: Default='Sun'. PyEphem item to search for and return results for.
        :type item: string
        :return: Pointer to array of all devices for requested device type
        :rtype: dict
        """
        if 'item' not in kwargs:
            raise InvalidArgumentError("Missing 'item' argument.")
        item = kwargs['item']
        dayOffset = 0
        if 'dayOffset' in kwargs:
            dayOffset = kwargs['dayOffset']

        try:
            obj = getattr(ephem, item)
        except AttributeError:
            raise AttributeError("PyEphem doesn't have requested item: %s" % item)
        self.obs.date = datetime.utcnow() + timedelta(days=dayOffset)
        temp = self._next_rising(self.obs, obj())
        return self._timegm(temp)

    def item_set(self, **kwargs):
        """
        Returns when an item sets.

        **Usage**:

        .. code-block:: python

            pluto_set = self._Times.item_set(dayOffset=0, item='Pluto') # the NEXT (0) setting of Pluto.

        :raises InvalidArgumentError: Raised if an argument is invalid or illegal.
        :raises AttributeError: Raised if PhPhem doesn't have the requested item.
        :param dayOffset: Default=0. How many days in future to find when item sets. 0 = Today, 1=Tomorrow, etc, -1=Yesterday
        :type dayOffset: int
        :param item: Default='Sun'. PyEphem item to search for and return results for.
        :type item: string
        :return: Pointer to array of all devices for requested device type
        :rtype: dict
        """
        if 'item' not in kwargs:
            raise InvalidArgumentError("Missing 'item' argument.")
        item = kwargs['item']
        dayOffset = 0
        if 'dayOffset' in kwargs:
            dayOffset = kwargs['dayOffset']

        try:
            obj = getattr(ephem, item)
        except AttributeError:
            raise AttributeError("PyEphem doesn't have requested item: %s" % item)
        # we want the date part only, but date.today() isn't UTC.
        self.obs.date = datetime.utcnow() + timedelta(days=dayOffset)

        temp = self._next_setting(self.obs, obj())
        return self._timegm(temp)

    def sunrise(self, **kwargs):
        """
        Return sunrise, optionaly returns sunrise +/- # days. The offset of "0" would be
        for the next sunrise.
        :param dayOffset: Default=0. How many days to offset. 0 would be next, -1 is today.
        :type dayOffset: int
        :param item: Default='Sun'. PyEphem item to search for and return results for.
        :type item: string
        """
        dayOffset = kwargs.get('dayOffset', 0)
        return self.item_rise(dayOffset=dayOffset, item='Sun')

    def sunset(self, **kwargs):
        """
        Return sunset, optionaly returns sunset +/- # days.

        :param dayOffset: Default=0. How many days to offset. 0 would be next, -1 is today.
        :type dayOffset: int
        :param item: Default='Sun'. PyEphem item to search for and return results for.
        :type item: string
        """
        dayOffset = 0
        if 'dayOffset' in kwargs:
            dayOffset = kwargs['dayOffset']
        return self.item_set(dayOffset=dayOffset, item='Sun')

    def sunrise_twilight(self, **kwargs):
        """
        Return sunrise, optionally returns sunrise +/- # days.

        :raises AttributeError: Raised if PhPhem doesn't have the requested item.
        :param dayOffset: Default=0. How many days to offset. 0 would be next, -1 is today's. But not always, on polar day this would be wrong
        :type dayOffset: int
        :param item: Which item to return information on. Sun, Moon, Mars, Jupiter, etc.
        :type item: string
        """
        dayOffset = 0
        if 'dayOffset' in kwargs:
            dayOffset = kwargs['dayOffset']
        item = 'Sun'
        if 'item' in kwargs:
            item = kwargs['item']

        try:
            obj = getattr(ephem, item)
        except AttributeError:
            raise AttributeError("PyEphem doesn't have requested item: %s" % item)

        self.obsTwilight.date = datetime.utcnow() + timedelta(days=dayOffset)
        temp = self._next_rising(self.obsTwilight, obj(), use_center=True)
        return self._timegm(temp)

    def sunset_twilight(self, **kwargs):
        """
        Return sunset, optionaly returns sunset +/- # days.

        :raises AttributeError: Raised if PhPhem doesn't have the requested item.
        :param dayOffset: Default=0. How many days to offset. 0 would be next, -1 is today's. But not always, on polar day this would be wrong
        :type dayOffset: int
        :param item: Which item to return information on. Sun, Moon, Mars, Jupiter, etc.
        :type item: string
        """
        dayOffset = 0
        if 'dayOffset' in kwargs:
            dayOffset = kwargs['dayOffset']
        item = 'Sun'
        if 'item' in kwargs:
            item = kwargs['item']

        try:
            obj = getattr(ephem, item)
        except AttributeError:
            raise AttributeError("PyEphem doesn't have requested item: %s" % item)

        # we want the date part only, but date.today() isn't UTC.
        dt = datetime.utcnow() + timedelta(days=dayOffset)
        self.obsTwilight.date = dt
        temp = self._next_setting(self.obsTwilight, obj(), use_center=True)
        return self._timegm(temp)

    def _setup_moon_events(self):
        """
        Setup events to be called when moon rise/set needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
        This is different than day/night since it accounts for twilight.
        """
        moonrise = self.item_rise(item='Moon')
        moonset = self.item_set(item='Moon')
        cur_time = time.time()

        if self.is_now_init:
            self.next_moonrise = moonrise
            self.next_moonset = moonset
            # print("_setup_moon_events and is_now_init: sunvisiable: %s" % self.item_visible(item='Sun'))
            self.is_moon_visible = self.item_visible(item='Moon')

        if self.item_visible(item='Moon'):
            reactor.callLater(moonset-cur_time+0.1, self._send_now_moonset)
            reactor.callLater(moonset-cur_time+1, self._setup_moon_events)
        else:
            reactor.callLater(moonrise-cur_time+0.1, self._send_now_moonrise)
            reactor.callLater(moonrise-cur_time+1, self._setup_moon_events)

    def _setup_light_dark_events(self):
        """
        Setup events to be called when is_light and is_dark needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
        This is different than day/night since it accounts for twilight.
        """
        cur_time = time.time()
        sunset = self.sunset_twilight()
        sunrise = self.sunrise_twilight()

        self._CalcLightDark()
        if self.is_now_init:
            # print("_setup_light_dark_events and is_now_init: sunvisiable: %s" % self.item_visible(item='Sun'))
            # print("_setup_light_dark_events and is_now_init: moon: %s" % self.item_visible(item='Moon'))
            self.is_sun_visible = self.item_visible(item='Sun')
            self.next_dark = sunset
            self.next_light = sunrise

        if self.is_light:
            reactor.callLater(sunset-cur_time+0.1, self._send_now_dark)
            reactor.callLater(sunset-cur_time+1, self._setup_light_dark_events)
        else:
            reactor.callLater(sunrise-cur_time+0.1, self._send_now_light)
            reactor.callLater(sunrise-cur_time+1, self._setup_light_dark_events)

            #set a callLater to redo islight/dark, and setup next broadcast.

    def _setup_day_night_events(self):
        """
        Setup events to be called when is_day and is_night needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
        This is different than light/dark since this doesn't account
        for twilight.
        """
        self._CalcDayNight()
        cur_time = time.time()
        sunset = self.sunset()
        sunrise = self.sunrise()

        if self.is_now_init:
            self.next_sunrise = sunrise
            self.next_sunset = sunset
            self.next_night = sunset
            self.next_day = sunrise

        if self.is_day:
            # logger.debug("NowNight event in: {setTime}", setTime=setTime)
            reactor.callLater(sunset-cur_time+0.1, self._send_now_night)
            reactor.callLater(sunset-cur_time+1, self._setup_day_night_events)
        else:
            # logger.debug("NowDay event in: {setTime}", setTime=setTime)
            reactor.callLater(sunrise-cur_time+0.1, self._send_now_day)
            reactor.callLater(sunrise-cur_time+1, self._setup_day_night_events)


            #set a callLater to redo isday/night, and setup next broadcast.

    ###  This function is not complete.  Need to calculate when the next
    ###  twilight period is. I just copied setupDayNightEvents to here for now.
    # When fixed, remove self._CalcTwilight() from def_setup_next_dawn_dusk_event
    def _setup_next_twilight_events(self):
        """
        Setup events to be called when is_twilight needs to change.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
        This is different than light/dark since this doesn't account
        for twilight.
        """
        self._CalcDayNight()
        self._CalcTwilight()  #is it twilight right now?
        cur_time = time.time()
        if self.is_twilight:
            setTime = self.sunset_twilight() + 1.1
            riseTime = self.sunrise() + 1.1
            twTime = min(setTime, riseTime)
            logger.debug("nowNotTwilight event in: {twTime}", twTime=twTime)
            reactor.callLater(twTime-cur_time, self.send_event_hook, 'now_twilight_end')
            reactor.callLater(twTime-cur_time+1, self._setup_next_twilight_events)
            self.next_twilight_end = twTime

            setTime = self.sunset() + 1.1
            riseTime = self.sunrise_twilight() + 1.1
            twTime = min(setTime, riseTime)
            self.next_wilight_start = twTime

        else:
            setTime = self.sunset() + 1.1
            riseTime = self.sunrise_twilight() + 1.1
            twTime = min(setTime, riseTime)
            logger.debug("nowTwilight event in: {twTime}", twTime=twTime)
            reactor.callLater(twTime-cur_time, self.send_event_hook, 'now_twilight_start')
            reactor.callLater(twTime-cur_time+1, self._setup_next_twilight_events)
            self.next_wilight_start = twTime

            setTime = self.sunset_twilight() + 1.1
            riseTime = self.sunrise() + 1.1
            twTime = min(setTime, riseTime)
            self.next_twilight_end = twTime


    def _setup_next_dawn_dusk_event(self):
        """
        Setup events to be called when it's either dawn, notdawn, dusk,
        and notdusk.
        Two callLater's are setup: one to send a broadcast event of the change
        the second callLater is to come back to this function and redo it all.
        """
        if self.is_now_init is False:
            self._CalcTwilight()  #is it twilight right now?

        sunrise = self.sunrise_twilight() # for today
        sunset = self.sunset()  # for today

        sunrise_end = self.sunrise() # for today
        sunset_end = self.sunset_twilight()  # for today
        logger.debug("_setup_next_dawn_dusk_event - Sunset: {sunset}", sunset=sunset)
        curtime = time.time()
        # First, determine we are closer to sunrise or sunset
        secsRise = sunrise - curtime#here
        secsSet = sunset - curtime

        secsRiseEnd = sunrise_end - curtime#here
        secsSetEnd = sunset_end - curtime
        if self.is_twilight == True: # It's twilight. Sun is down.
            if secsRiseEnd < secsSetEnd: #  it's dawn right now = twilight + closer to sunrise's end
                reactor.callLater(secsRiseEnd+1.1, self._send_now_dawn_end) # set a timer for no more dawn
                reactor.callLater(secsRiseEnd+2, self._setup_next_dawn_dusk_event)
                if self.is_now_init:
                    self.is_dawn = True
                    self.is_dusk = False
            else: # else, closer to sunset.
                self.CLnowNotDusk = reactor.callLater(secsSetEnd+1.1, self._send_now_dusk_end) # set a timer for no more dusk
                reactor.callLater(secsSetEnd+2, self._setup_next_dawn_dusk_event)
                if self.is_now_init:
                    self.is_dawn = False
                    self.is_dusk = True
        else: # it's not twilight, we need to set a time for it to start.
            if self.is_now_init:
                self.is_dawn = False
                self.is_dusk = False

            if secsRise < secsSet: #  it's going to be dawn next = no twilight + closer to sunrise
                self.CLnowDawn = reactor.callLater(secsRise+1.1, self._send_now_dawn_start) # set a timer for is dawn
                reactor.callLater(secsRise+2, self._setup_next_dawn_dusk_event)
            else: # else, we are closer to sunset!
                self.CLnowDusk = reactor.callLater(secsSet+1.1, self._send_now_dusk_start) # set a timer for is dusk
                reactor.callLater(secsSet+2, self._setup_next_dawn_dusk_event)
        logger.debug("Start next twilight in: rise begins {secsRise} (set begins {secSet}), stop next twilight: rise ends {secsRiseEnd} (set ends {secSetEnd})",
                     secsRise=secsRise, secsSet=secsSet, secsRiseEnd=secsRiseEnd, secsSetEnd=secsSetEnd)

    def _setup_weekday_events(self):
        """
        Sets "is.weekday" and "is.weekend" states. Also setups up "day_of_week" for mon-sun.
        """
        day_map = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday',
        }

        day_number = datetime.today().weekday()

        if day_number < 5:
            self.is_weekday = True
            self.is_weekend = False
        else:
            self.is_weekday = False
            self.is_weekend = True

        self.day_of_week = day_map[day_number]
        reactor.callLater(dt.get_next_time('12:00am')[0] - time.time(), self._setup_weekday_events)

    def _send_now_night(self):
        """
        Called by timer when the sunsets. Called by: _setup_sun_events
        """
        self.is_sun_visible = False
        self.next_sunset = self.item_set(item='Sun')
        self.send_event_hook('now_night')
        self.send_event_hook('now_day')

    def _send_now_day(self):
        """
        Called by timer when the sunrises. Called by: _setup_sun_events
        """
        # print("_send_now_day")
        self.is_sun_visible = True
        self.next_sunrise = self.item_set(item='Moon')
        self.send_event_hook('now_sunrise')
        self.send_event_hook('now_sunrise')

    def _send_now_moonset(self):
        """
        Called by timer when the moon sets. Called by: _setup_moon_events
        """
        self.is_moon_visible = False
        self.next_moonset = self.item_set(item='Moon')
        self.send_event_hook('now_moonset')

    def _send_now_moonrise(self):
        """
        Called by timer when the moon risess. Called by: _setup_moon_events
        """
        self.is_moon_visible = True
        self.next_moonrise = self.item_rise(item='Moon')
        self.send_event_hook('now_moonrise')

    def _send_now_dark(self):
        """
        Called by timer when it's nowNotDusk. Calles _setupNextTwlightEvents
        to setup the next twilight cycle for dawn.
        """
        self.next_dark = self.sunset_twilight()
        self.send_event_hook('now_dark')

    def _send_now_light(self):
        """
        Called by timer when it's nowNotDusk. Calles _setupNextTwlightEvents
        to setup the next twilight cycle for dawn.
        """
        self.next_light = self.sunrise_twilight()
        self.send_event_hook('now_light')

    def _send_now_dusk_start(self):
        """
        Called by timer when it's nowDusk.
        """
        self.is_dusk = True
        self.send_event_hook('now_dusk_start')

    def _send_now_dusk_end(self):
        """
        Called by timer when it's nowNotDusk. Calles _setupNextTwlightEvents
        to setup the next twilight cycle for dawn.
        """
        self.is_dusk = False
        self.send_event_hook('now_dusk_end')

    def _send_now_dawn_start(self):
        """
        Called by timer when it's nowDawn.
        """
        self.is_dawn = True
        self.send_event_hook('now_dawn_start')

    def _send_now_dawn_end(self):
        """
        Called by timer when it's nowNotDawn. Calls _setupNextTwlightEvents
        to setup the next twilight cycle for dusk.
        """
        self.is_dawn = False
        self.send_event_hook('now_dawn_end')

    def send_event_hook(self, event_msg):
        """
        Generate an "event" message of status type being the time
        event name.

        **Hooks called**:

        * _time_event_ : Sends kwargs: *key* - The name of the state being set. *value* - The new value to set.

        """
        if self.is_now_init is False:
            try:
                global_invoke_all('_time_event_',
                                  called_by=self,
                                  value=event_msg,
                                  stoponerror=True,
                                  )
            except YomboHookStopProcessing:
                logger.warn("Stopping processing 'send_event_hook' due to YomboHookStopProcessing exception.")
                return

    def _CalcTwilight(self):
        """
        Sets the class variable "is_twilight" depending if it's
        twilight right now. This is called everytime gateway starts
        and when the last twilight has ended.

        schematically:

        set - setting time
        rise - rising time
        Tset - setting of obsTwilight
        Trise - rising of obsTwilight
        N(x) - next, e.g. N(rise) -- next rising, N(Tset) -- next setting of obsTwilight

        -->>>----Time flow--->>>>-----

               |TWILIGHT    |     NIGHT         |TWILIG|   DAY        |TWILIGHT|       NIGHT       |TWILIGHT |   DAY        |TWILIGHT  |    NIGHT
               |            |                   |      |              |        |                   |         |              |          |
              set                                     rise           set                                    rise           set
               |---------------------------------------|              |--------------------------------------|              |---------------------------------------
               |      N(set)>N(rise)                   |N(set)<N(rise)|       N(set)>N(rise)                 |N(set)<N(rise)|        N(set)>N(rise)

        --------------------|                   |------------------------------|                   |-----------------------------------|
                          Tset                Trise                           Tset                Trise                               Tset
        N(Tset)<N(Trise)    | N(Tset)>N(Trise)  |  N(Tset)<N(Trise)            | N(TSet)>N(Trise)  |      N(Tset) < N(Trise)           |

        So the TWILIGHT events occur when (N(set)>N(rise) AND  N(Tset)<N(Trise))
        This condition should work on polar day/night also.
        """
        self.obs.date = datetime.utcnow()
        self.obsTwilight.date = datetime.utcnow()

        if self._next_setting(self.obsTwilight,ephem.Sun(),use_center=True) < self._next_rising(self.obsTwilight,ephem.Sun(),use_center=True) \
          and \
          self._next_setting(self.obs,ephem.Sun()) > self._next_rising(self.obs,ephem.Sun()):
            self.is_twilight = True
        else:
            self.is_twilight = False

    def _CalcLightDark(self):
        """
        Sets the is_light and is_dark vars.  It's light if the sun is up and it's twilight.
        """
        self.obs.date = datetime.utcnow()
        self.obsTwilight.date = datetime.utcnow()
        #logger.info("is_light: %s < %s", self._previous_rising(self.obsTwilight,ephem.Sun(),use_center=True),
        #            self._previous_setting(self.obsTwilight,ephem.Sun(),use_center=True))

        if self._previous_rising(self.obsTwilight,ephem.Sun(),use_center=True) < self._previous_setting(self.obsTwilight,ephem.Sun(),use_center=True):
            self.is_light = False
            self.is_dark = True
        else:
            self.is_light = True
            self.is_dark = False

    def _CalcDayNight(self):
        """
        Sets up is_day and is_night. Is day if the sun is not below horizon.
        """
        self.obs.date = datetime.utcnow()
        self.obsTwilight.date = datetime.utcnow()
        if self._previous_rising(self.obs, ephem.Sun()) < self._previous_setting(self.obs, ephem.Sun()):
            self.is_day = False
            self.is_night = True
        else:
            self.is_day = True
            self.is_night = False

    # These wrappers need for polar regions where day might be longer than 24 hours
    def _previous_rising(self, observer, item, use_center=False):
        return self._riset_wrapper(observer,'previous_rising',item,use_center=use_center)

    def _previous_setting(self, observer: dict(type=float, help='the dividend'), item, use_center=False):
        return self._riset_wrapper(observer,'previous_setting',item,use_center=use_center)

    def _next_rising(self, observer, item, use_center=False):
        return self._riset_wrapper(observer,'next_rising',item,use_center=use_center)

    def _next_setting(self, observer, item, use_center=False):
        return self._riset_wrapper(observer,'next_setting',item,use_center=use_center)
    def _riset_wrapper(self, observer, obsf_name, obj,use_center=False):
        save_date = observer.date #we need to save this date to compare with later
        while True:
            try:
                dt = getattr(observer,obsf_name)(obj,use_center=use_center)
                observer.date = save_date
                return dt
            except (ephem.AlwaysUpError,ephem.NeverUpError):
                if (observer.date < save_date - 365) or (observer.date > save_date + 365):
                    # print('Could not find daylight bounds, last checked date ', observer.date, ', first checked ', save_date,' - year checked day by day.')
                    raise #It is not possible to found setting or rising
                continue

    def _timegm (self, dt):
        return CalTimegm(dt.tuple())


#******************************************************************************************************
#************************************ TESTS  **********************************************************
#******************************************************************************************************
    def runned_for_tests(self):
        """
        Patch reactor.callLater to be a simple print for tests
        """
        #        self.call_arr = []
        self.call_dict = {}
        from _thread import allocate_lock
        self.mutex = allocate_lock()
        self.uniq = 1
        self.show_messages = True
        def callLaterMy (a,b,c=None):
            assert a>0, "callLater will fail if secondsOffset <= 0 (%s)" % a
            coef = time.time()
            self.mutex.acquire()
            if (self.show_messages):
                print('calling reactor.callLater (', a, b, c, ')')
            #            self.call_arr.append((a,b,c))
            if (a+coef in self.call_dict):
                self.call_dict[a+coef] = self.call_dict[a+coef] + [(float(a+coef),b,c,self.uniq)]
            else:
                self.call_dict[a+coef] = [(float(a+coef),b,c,self.uniq)]
            if (self.show_messages):
                print(('calling in %s:%s:%s.%s - ' % (int(a/60/60),int(a/60)%60,int(a)%60,int(a*1000)%1000)), datetime.utcnow() + timedelta(seconds=a))
            self.uniq = self.uniq + 1
            self.mutex.release()

        self._reactor_callLater = getattr(reactor,'callLater')
        setattr(reactor, 'callLater', callLaterMy)

        self.year_array = [0]*(365*24)
        self.start_time = time.time()
        def send_event_hook_my(a):
            #print 'send_event_hook %s on %s' % (a, datetime.fromtimestamp(time.time()))
            ct = int ((time.time() - self.start_time) / 60 / 60)
            #print 'send_event_hook %s on %s' % (a, datetime.fromtimestamp(time.time()))
            if (ct >= (365*24)):
                return
            if (a == 'nowDark'):
                assert (self.year_array[ct] & 1) == 0, "nowDark duplicate"
                self.year_array[ct] = self.year_array[ct] | 1
            if (a == 'nowLight'):
                assert (self.year_array[ct] & 2) == 0, "nowLight duplicate"
                self.year_array[ct] = self.year_array[ct] | 2
            if (a == 'nowNight'):
                assert (self.year_array[ct] & 4) == 0, "nowNight duplicate"
                self.year_array[ct] = self.year_array[ct] | 4
            if (a == 'nowDay'):
                assert (self.year_array[ct] & 8) == 0, "nowDay duplicate"
                self.year_array[ct] = self.year_array[ct] | 8
            if (a == 'nowTwilight'):
                assert (self.year_array[ct] & 16) == 0, "nowTwilight duplicate"
                self.year_array[ct] = self.year_array[ct] | 16
            if (a == 'nowNotTwilight'):
                assert (self.year_array[ct] & 32) == 0, "nowNotTwilight duplicate"
                self.year_array[ct] = self.year_array[ct] | 32
            if (a == 'nowDawn'):
                assert (self.year_array[ct] & 64) == 0, "nowDawn duplicate"
                self.year_array[ct] = self.year_array[ct] | 64
            if (a == 'nowNotDawn'):
                assert (self.year_array[ct] & 128) == 0, "nowNotDawn duplicate"
                self.year_array[ct] = self.year_array[ct] | 128
            if (a == 'nowDusk'):
                assert (self.year_array[ct] & 256) == 0, "nowDusk duplicate"
                self.year_array[ct] = self.year_array[ct] | 256
            if (a == 'nowNotDusk'):
                assert (self.year_array[ct] & 512) == 0, "nowNotDusk duplicate"
                self.year_array[ct] = self.year_array[ct] | 512
        self.send_event_hook_old = getattr(self, 'send_event_hook')
        setattr(self, 'send_event_hook', send_event_hook_my)

    def finish_tests(self):
        setattr(reactor, 'callLater', self._reactor_callLater)
        setattr(self, 'send_event_hook', self.send_event_hook_old)

    def run_inner_tests_chk_year(self, set_olddt, set_newdt, lat, lon):
        print('************check year: lat = %s, lon = %s *********************' % (lat,lon))

        globals()['time'] = lambda:t
        self.obs.lat = lat
        self.obs.lon = lon
        self.obsTwilight.lat = lat
        self.obsTwilight.lon = lon

        #        globals()['datetime'] = old_datetime
        set_olddt()
        midnight_utc = datetime.utcnow().date()
        midday_utc = datetime.utcnow().date() + timedelta(hours=12)
        #        globals()['datetime'] = DateTime
        set_newdt()
        t = CalTimegm (midnight_utc.timetuple())

        err = 0
        print('Year check results (. - ok, X - should be day but night, x - should be night):[', midnight_utc,']', end=' ')
        for i in range (0,366): #check night is night and day is day
            #midnight
            self._CalcDayNight()
            if (self.is_night): print('.', end=' ')
            else:
                print('x', end=' ')
                err = err + 1
            t = t + 60*60*12
            #midday
            self._CalcDayNight()
            if (self.is_day): print('.', end=' ')
            else:
                print('X', end=' ')
                err = err + 1
            t = t + 60*60*12

        print('Errors:', err)

        # parameters: latm lon, date that day, twilight begin time, sunrise, sunset, twilight end time
    def table_check(self,lat,lon,dt,twb,psr,nss,twe,msg,sun_hor='0'):
        print('checking table times for ', msg)
        print('lat = %s, lon = %s, dt = %s, twb = %s, psr = %s, nss = %s, twe = %s, horizon correction = %s' % (lat,lon,dt,twb,psr,nss,twe,sun_hor))
        d = lambda x:datetime.strptime(x,'%Y/%m/%d %H:%M:%S')
        t = CalTimegm(d(dt).timetuple())
        globals()['time'] = lambda:t

        #to check tables we should regulate pressure
        self.obs.temp = 0
        self.obs.pressure = 0
        self.obs.lat = lat
        self.obs.lon = lon
        self.obs.horizon = sun_hor
        self.obsTwilight.temp = 0
        self.obsTwilight.pressure = 0
        self.obsTwilight.horizon = '-6'
        self.obsTwilight.lat = lat
        self.obsTwilight.lon = lon

        err_ss = self.sunset () - CalTimegm(d(nss).timetuple())
        err_twe = self.sunset_twilight () - CalTimegm(d(twe).timetuple())
        assert (abs(err_ss) < 120), "time skew is more than 2 minutes for sunset (%s) calculated(lt) = %s should be(lt) = %s" % (msg,datetime.fromtimestamp(self.sunset()),datetime.fromtimestamp(CalTimegm(d(nss).timetuple())))
        assert (abs(err_twe) < 120), "time skew is more than 2 minutes for twilight finish (%s) calculated(lt) = %s should be(lt) = %s" % (msg,
                                                                                                                                           datetime.fromtimestamp(self.sunset_twilight ()),
                                                                                                                                           datetime.fromtimestamp(CalTimegm(d(twe).timetuple())))

        err_sr = CalTimegm(self._previous_rising(self.obs,ephem.Sun()).tuple()) - CalTimegm(d(psr).timetuple())
        err_twb = CalTimegm(self._previous_rising(self.obsTwilight,ephem.Sun(),use_center=True).tuple()) - CalTimegm(d(twb).timetuple())

        assert (abs(err_sr) < 120), "time skew is more than 2 minutes for sunrise (%s)" % msg
        assert (abs(err_twb) < 120), "time skew is more than 2 minutes for twilight start (%s)" % msg
        print('table check passed')
        self.obs.pressure = 1010
        self.obsTwilight.pressure = 1010
        self.obs.horizon='0'
        self.obs.temp = 15
        self.obsTwilight.temp = 15
    def run_inner_tests(self):
        print(self.obs)
        print(self.obsTwilight)
        print('time.time()', time.time())
        print('sr', self.sunrise())
        print('ss', self.sunset())
        print('srt', self.sunrise_twilight())
        print('sst', self.sunset_twilight())
        assert (self.sunrise()>time.time()),"next rise after current time"
        assert (self.sunset()>time.time()),"next set after current time"
        assert (self.sunrise_twilight()>time.time()),"next twilight rise after current time"
        assert (self.sunset_twilight()>time.time()),"next twilight set after current time"

        print('************Year check midnights********************')
        old_time=globals()['time']
        old_datetime = globals()['datetime']
        class DateTime(datetime):
            @staticmethod
            def utcnow():
                return datetime.utcfromtimestamp(time.time())
            @staticmethod
            def now():
                return datetime.fromtimestamp(time.time())
            def timetuple(self):
                return(self.year, self.month, self.day, self.hour, self.minute, self.second + self.microsecond / 1000000.0)
        globals()['datetime'] = DateTime
        globals()['time'] = lambda:t

        print('************adding day*********************')

        globals()['datetime'] = old_datetime
        t = CalTimegm (datetime.utcnow().timetuple()) + 24*60*60
        globals()['datetime'] = DateTime
        print('time.time()', time.time())
        print('sr', self.sunrise())
        print('ss', self.sunset())
        print('srt', self.sunrise_twilight())
        print('sst', self.sunset_twilight())

        def _set_dt(dt):
            globals()['datetime'] = dt

        set_olddt = lambda:_set_dt(old_datetime)
        set_newdt = lambda:_set_dt(DateTime)

        #Greenwich ecuator
        self.run_inner_tests_chk_year(set_olddt, set_newdt, '0', '0')

        #Murmansk lat
        self.run_inner_tests_chk_year(set_olddt, set_newdt, '69', '0')

        #near north pole
        #        self.run_inner_tests_chk_year(set_olddt, set_newdt, '89:30', '0')

        #check Atlanta
        self.obs.lat = '33.8'
        self.obs.lon = '-84.4'
        self.obsTwilight.lat = '33.8'
        self.obsTwilight.lon = '-84.4'
        t = CalTimegm (datetime (2009,9,6,17,0).timetuple())

        globals()['time'] = lambda:t #renew closure

        print('************table check********************')

        self.table_check('33.8','-84.4','2009/09/06 17:00:00','2009/09/06 10:50:00','2009/09/06 11:15:00','2009/09/06 23:56:00','2009/09/07 00:21:00','Atlanta','-0:34')
        #        self.table_check('68.95','33.1','2013/08/12 12:00:00','2013/08/11 22:18:13','2013/08/12 00:44:48','2013/08/12 19:03:14','2013/08/12 21:10:48','Murmansk','-0:50')

        print('************callLater check********************')

        self.obs.lat = '33.8'
        self.obs.lon = '-84.4'
        self.obs.pressure = 0
        self.obs.temp = 0
        self.obs.pressure = 0
        self.obs.horizon = '-0:34'
        self.obsTwilight.lat = '33.8'
        self.obsTwilight.lon = '-84.4'
        self.obsTwilight.pressure = 0
        self.obsTwilight.temp = 0
        self.obsTwilight.horizon = '-6:0'
        self.mutex.acquire()
        self.call_dict = {} #reset call array
        self.mutex.release()
        #set some timw point (now will be good enough!)
        globals()['datetime'] = old_datetime
        t = CalTimegm (datetime.utcnow().timetuple())
        globals()['datetime'] = DateTime
        globals()['time'] = lambda:t #renew closure

        self.year_array = [0]*(365*24)

        self.init(self._Loader)

        #        print self.call_arr
        #print self.call_dict

        #iterate callLater events
        old_events = []
        self.start_time = time.time()

        self.show_messages = False
        for i in range (0,2000):
            self.mutex.acquire()
            #print "On %s iteration there are %s later calls" % (i, len(self.call_dict))
            def prnDict():
                for s in list(self.call_dict.keys()):
                    print('dict[%s]:' % datetime.fromtimestamp(s))
                    c_l = self.call_dict[s]
                    for (a,b,c,d) in c_l:
                        #print 'check ', c
                        print("%s --- func = %s, param = %s" % (d,b,c))
            #prnDict()
            assert (len(self.call_dict) > 0), 'no more laterCalls on %s iteration' % i
            t_corr_l = list(self.call_dict.keys())
            assert (t_corr_l[0] > 0), "bad value of seconds in laterCall: %s" % t_corr_l[0]

            #check dict (there should not be fully duplicate events (or should?))
            to_call_list = []
            #print 'dict check: ', t_corr_l
            for s in list(self.call_dict.keys()):
                #print 'check second = %s' % s
                c_l = self.call_dict[s]
                to_call_list = to_call_list + c_l
                for (a,b,c,d) in c_l:
                    #print 'check ', c
                    assert ((a,b,c) not in old_events), "laterCall is duplicated:%s,%s,%s (u=%s)" % (a,b,c,d)
                    old_events = old_events + [(a,b,c)]
            self.call_dict = {} #clear call dict

            #print 'dict calls'
            self.mutex.release()
            #call functions on that time
            old_t = t
            for (tm,func,par,u) in to_call_list:
                t = tm
                if par is None:
                    func()
                else:
                    func(par)
            t = old_t

        ya = self.year_array
        print("Year table:")
        print(" 0-23 - hour number (utc); for each hour events(sent messages) are shown: R/L - Dark/Light, N/D - Night/Day, W/w - Twilight/NotTwilight, A/a - Dawn/NotDawn, U/u - Dusk/NotDusk.")
        print(" Upper left corner of table is current hour. ")
        print("0     1     2     3     4     5     6     7     8     9    10    11    12    13    14    15    16    17    18    19    20    21    22    23")
        rc = [0]*10
        for li in [ya[i:i+24] for i in range(0,len(ya),24)]:
            for c in li:
                for p in range(0,10):
                    if (c & (1 << p) > 0):
                        rc [p] = rc [p] + 1
                l = ''
                if (c & 1) > 0 : l = l + 'R'
                elif (c & 2) > 0 : l = l + 'L'
                else: l = l + ' '

                if (c & 4) > 0 : l = l + 'N'
                elif (c & 8) > 0 : l = l + 'D'
                else: l = l + ' '

                if (c & 48) == 48: l = l + '+'
                elif (c & 16) > 0 : l = l + 'W'
                elif (c & 32) > 0 : l = l + 'w'
                else: l = l + ' '

                if (c & 192) == 192: l = l + '/'
                elif (c & 64) > 0 : l = l + 'A'
                elif (c & 128) > 0 : l = l + 'a'
                else: l = l + ' '

                if (c & 768) == 768: l = l + '\\'
                elif (c & 256) > 0 : l = l + 'U'
                elif (c & 512) > 0 : l = l + 'u'
                else: l = l + ' '
                print("%s"%l, end=' ')
            print()

        print('indeces in result count: 0-Dark,1-Light,2-Night,3-Day,4-Twilight,5-NotTwi,6-Dawn,7-NotDawn,8-Dusk,9-NotDusk')
        print('result count = ', rc)
        globals()['time']=old_time
        globals()['datetime'] = old_datetime
        self.finish_tests() #revert reactor.callLater patch