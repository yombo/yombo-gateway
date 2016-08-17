# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Cron Tab @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Cron_Tab>`_

Cron like library that can be used to perform activites. Can be used by modules to call a function at set times.

Idea and partial code from: http://stackoverflow.com/questions/373335/suggestions-for-a-cron-like-scheduler-in-python

You can create a new cronjob by specifing which function to call, specify the second, minute,
hour, day, month, day of week (dow), along with args and kwargs to send to function.  Not all
items need to specified. If time elements are not set, then it's assumed to be * (all).

Examples:

.. code-block:: python

   #  M H D M DOW
   #  * * * * *  # call every minute, every hour, every day, every month
   self._CronTab.new(self.myFunction)

   # */2 * * * *  # call every other minute)
   myArgs=('arg1', 'arg2')
   self._CronTab.new(self.myFunction, min=range(0, 59, 2), args=myArgs)  # use range and specify a step
   # The range just creates a list of minutes. You can also just pass a list of numbers.

   # 0 0,6,12,18 * * *  # at midnight, 6am, 12pm, 6pm
   # myKwargs={"argument1" : "value1", "argument2" : "value2"}
   self._CronTab.new(self.myFunction, min=0, hour=(0,6,12,18), kwargs=myKwargs)  # Notice the list of hours to run.

   # 0 12 * 0 0 # at 12:00pm on sunday
   self._CronTab.new(self.myFunction, min=0, hour=12, dow=0 )  # use range and specify a step

   # 0 12 * 0 0 # at 12:00pm on sunday
   self._CronTab.new(self.myFunction, min=0, hour=12, dow=0 )  # use range and specify a step

Usage example

.. code-block:: python

   self.MyCron = self._CronTab.new(self.myFunction, min=0, hour=12, dow=0 )

   #want to disable for a while..
   self.MyCron.disable()

   #re-enable it
   self.MyCron.enable()

   #label it
   self.MyCron.label = "modules.myModule.Lunchtime on Sundays"

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2013-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from datetime import datetime, timedelta

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor


# Import Yombo libraries
from yombo.utils import random_string
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.exceptions import YomboFuzzySearchError, YomboCronTabError
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.crontab')

# Some utility classes / functions first
class AllMatch(set):
    """Universal set - match everything"""
    def __contains__(self, item): return True

allMatch = AllMatch()

def conv_to_set(obj):  # Allow single integer to be provided
    if isinstance(obj, str) and obj == '*': # return AllMatch
        return conv_to_set(AllMatch) 
    if isinstance(obj, (int,long)):
        return set([obj])  # Single item
    if not isinstance(obj, set):
        obj = set(obj)
    return obj

class CronTab(YomboLibrary):
    """
    Manages all cron jobs.
    """
    def __getitem__(self, key):
        """
        Cron jobs are already accessible through a pre-defined variable
        in all modules: self._CronTab.

        To manage a cron job, you must know it's cron UUID or cron name:
            >>> self._CronTab['7s453hhxl3']  #by cron uuid
        or::
            >>> self._CronTab['module.YomboBot.MyCron']  #by name

        See: :func:`yombo.core.helpers.getCronTab` for full usage example.

        :param key: The cron UUID / cron job name
        :type key: string
        """
        
        return self._search(key)

    def _init_(self):
        """
        Setups up the basic framework.

        :param loader: A pointer to the Loader library.
        :type loader: Instance of Loader
        """
        self.__yombocron = {}
        
    def _load_(self):
        """
        Setup the looping call function.
        """
        self.__cronTabLoop = LoopingCall(self._checkCron)

    def _start_(self):
        """
        Start the looping call to check for cron every minute.
        """
        now = datetime.now()
        cron_next_minute =  now - timedelta(seconds = now.second - 61)  # we always run cron near the top of the minute
        cron_start = float(cron_next_minute.strftime('%s.%f')) - float(now.strftime('%s.%f')) - 0.2

        reactor.callLater(cron_start, self.setup_cron_loop)

    def setup_cron_loop(self):
        self.__cronTabLoop.start(60)

    def _checkCron(self):
        """
        Checks to see if cron needs to run anything.
        """
        logger.debug("Cron check: %s" % datetime.now())

        t=datetime(*datetime.now().timetuple()[:5])
        for e in self.__yombocron:
          self.__yombocron[e].check(t)

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _unload_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _search(self, cronRequested):
        """
        Attempts to find the cron job requested using a couple of methods.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find cron jobs: `self._CronTab['8w3h4sa']`

        See: :func:`yombo.core.helpers.getCronTab` for full usage example.
        
        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param cronRequested: The device UUID or device label to search for.
        :type cronRequested: string
        :return: Pointer to array to requested cron job.
        :rtype: dict
        """
        if cronRequested in self.__yombocron:
            return self.__yombocron[cronRequested]
        else:
            theCrons = FuzzySearch({}, .95)
            for cron in self.__yombocron:
              theCrons[cron] = self.__yombocron[cron]
            try:
              results = theCrons[cronRequested]
              if results['valid']:
                return self.__yombocron[results['key']]
            except YomboFuzzySearchError, e:
                raise YomboCronTabError('Searched for %s, but no good matches found. Best match: %s' % (e.searchFor, e.others[0].label) )
        raise YomboCronTabError('Searched for %s, but no matches found. ' % cronRequested )

    def new(self, crontab_callback, min=allMatch, hour=allMatch, day=allMatch,
            month=allMatch, dow=allMatch, label='', enabled=True, args=(),
            kwargs={}):
        """
        Add a new cronjob.

        :param crontab_callback: Function to call
        :type crontab_callback: Reference to function
        :param min: (optional) Minute to perform crontab_callback
        :type min: "*", int, or list of ints
        :param hour: (optional) Hour to perform crontab_callback
        :type hour: "*", int, or list of ints
        :param day: (optional) Day to perform crontab_callback
        :type day: "*", int, or list of ints
        :param month: (optional) Month to perform crontab_callback
        :type month: "*", int, or list of ints
        :param dow: (optional) Day of week to perform crontab_callback
        :type dow: "*", int, or list of ints
        :param label: (optional) Label for cron job.
        :type label: string
        :param enabled: (optional, default=True) If cronjob should be enabled.
        :type enabled: bool
        :param args: (optional) Arguments to pass to "crontab_callback"
        :type args: List of arguments
        :param kwargs: (optional) Keyword arguments to pass to "crontab_callback"
        :type kwargs: Dict of arguments
        """
        newCron = CronJob(crontab_callback, min=min, hour=hour, day=day, month=month,
            dow=dow, label=label, enabled=enabled, crontab=self, args=args,
            kwargs=kwargs)
        self.__yombocron[newCron.cronUUID] = newCron
        return newCron

    def remove(self, key):
        """
        Removes a cronjob. Accepts either cron uuid or cron name.

        To remove a cron (note, it's a method not a dictionary):
            >>> self._CronTab.remove('7s453hhxl3')  #by cron uuid
        or::
            >>> self._CronTab.remove('module.YomboBot.MyCron')  #by name

        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param key: The cron UUID / cron job name
        :type key: string
        """
        cronjob = self._search(key)
        cronjob.disable()
        del self.__yombocron[cronjob.cronUUID]

    def enable(self, key):
        """
        Enable a cronjob. Accepts either cron uuid or cron name.

        To enable a cron (note, it's a method not a dictionary):
            >>> self._CronTab.enable('7s453hhxl3')  #by cron uuid
        or::
            >>> self._CronTab.enable('module.YomboBot.MyCron')  #by name

        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param key: The cron UUID / cron job name
        :type key: string
        """
        cronjob = self._search(key)
        cronjob.enable()

    def disable(self, key):
        """
        Disable a cronjob. Accepts either cron uuid or cron name.

        To disable a cron (note, it's a method not a dictionary):
            >>> self._CronTab.disable('7s453hhxl3')  #by cron uuid
        or::
            >>> self._CronTab.disable('module.YomboBot.MyCron')  #by name

        :param key: The cron UUID / cron job name
        :type key: string
        """
        cronjob = self._search(key)
        cronjob.disable()


    def run_now(self, key):
        """
        Runs a cronjob now.

        To run a cron (note, it's a method not a dictionary):
            >>> self._CronTab.run_now('7s453hhxl3')  #by cron uuid
        or::
            >>> self._CronTab.run_now('module.YomboBot.MyCron')  #by name

        :param key: The cron UUID / cron job name
        :type key: string
        """
        cronjob = self._search(key)
        cronjob.runNow()

    def set_label(self, key, label):
        """
        Set job label.

        To set a label for a cron job:
            >>> self._CronTab.set_label('7s453hhxl3', 'modules.mymodule.mycronjob')  #by cron uuid

        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param key: The cron UUID
        :type key: string
        :param label: New label for cron job.
        :type label: string
        """
        cronjob = self._search(key)
        cronjob.label = label

    def run_at(self, crontab_callback, timestring, label='', args=(), kwargs={}):
        """
        Helper function for CronTab.new().

        Acceptable format for 'timestring' value.

        * 'HH:MM' (24 hour). EG: 21:10 (9:10pm)
        * 'h:mAM' EG: 1:14pm, 6:30am
        * 'h:m AM' EG: 1:14 pm, 6:30 am

        :param crontab_callback: Function to call
        :type crontab_callback: Reference to function
        :param timestring: String to parse to get hour:minute from
        :type timestring: string
        :param label: (optional) Label for cron job.
        :type label: string
        :param enabled: (optional, default=True) If cronjob should be enabled.
        :type enabled: bool
        :param args: (optional) Arguments to pass to "crontab_callback"
        :type args: List of arguments
        :param kwargs: (optional) Keyword arguments to pass to "crontab_callback"
        :type kwargs: Dict of arguments
        """
        dateObj = None
        try: # hh:mm
            try:
                dateObj = datetime.strptime(timestring, '%I:%M%p')
            except:
                try:
                    dateObj = datetime.strptime(timestring, '%I:%M %p')
                except:
                    dateObj = datetime.strptime(timestring, '%H:%M')
            return self.new(crontab_callback, dateObj.minute, dateObj.hour, label=label,
                   args=args, kwargs=kwargs)
        except:
          YomboCronTabError("Unable to parse time string. Try HH:MM (24 hour time) format")

class CronJob(object):
    """
    Individual cron job.  Manages by CronTab class.
    """
    def __init__(self, crontab_callback, min=allMatch, hour=allMatch, day=allMatch,
                       month=allMatch, dow=allMatch, label='',
                       enabled=True, crontab=None, args=(), kwargs={}):
        """
        Setup the cron event.
        """
        self.crontab_callback = crontab_callback
        self.mins = conv_to_set(min)
        self.hours= conv_to_set(hour)
        self.days = conv_to_set(day)
        self.months = conv_to_set(month)
        self.dow = conv_to_set(dow)
        self.label = label
        self.enabled = enabled
        self.crontab = crontab
        self.args = args
        self.kwargs = kwargs
        self.cronUUID = random_string(length=24)

    def __del__(self):
        """
        About to delete myself.  Going to disable myself and tell crontab about this
        if it's linked.
        """
        self.enabled = False
        if self.crontab is not None:
          self.crontab.remove(self.cronUUID)

    def enable(self):
        """
        Enable this cronjob.
        """
        self.enabled = True

    def disable(self):
        """
        Disable this cronjob.
        """
        self.enabled = False

    def match_time(self, t):
        """
        Return True if this event should trigger at the specified datetime
        """
        return ((t.minute     in self.mins) and
                (t.hour       in self.hours) and
                (t.day        in self.days) and
                (t.month      in self.months) and
                (t.weekday()  in self.dow))

    def check(self, t):
        if self.enabled is True and self.match_time(t):
            self._Statistics.increment("lib.crontab.jobs", bucket_time=15, anon=True)
            self.crontab_callback(*self.args, **self.kwargs)

    def runNow(self):
       self.crontab_callback(*self.args, **self.kwargs)
