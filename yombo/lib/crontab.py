# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `CronTab @ Library Documentation <https://yombo.net/docs/libraries/crontab>`_

Cron like library that can be used to perform scheduled actions. Can be used by modules to call a function at set times.

Idea and partial code from: http://stackoverflow.com/questions/373335/suggestions-for-a-cron-like-scheduler-in-python

You can create a new :class:`CronTask` by specifing which function to call, specify the second, minute,
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

:copyright: Copyright 2013-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/crontab.html>`_
"""
# Import python libraries
from datetime import datetime, timedelta

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor

# Import Yombo libraries
from yombo.utils import random_string
from yombo.core.exceptions import YomboWarning, YomboCronTabError
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance

logger = get_logger('library.crontab')

# Some utility classes / functions first
class AllMatch(set):
    """Universal set - match everything"""
    def __contains__(self, item): return True

allMatch = AllMatch()

def conv_to_set(obj):  # Allow single integer to be provided
    if isinstance(obj, str) and obj == '*': # return AllMatch
        return conv_to_set(AllMatch) 
    if isinstance(obj, int):
        return set([obj])  # Single item
    if not isinstance(obj, set):
        obj = set(obj)
    return obj

class CronTab(YomboLibrary):
    """
    Manages all cron jobs.

    All modules already have a predefined reference to this library as
    `self._CronTab`. All documentation will reference this use case.
    """
    def __contains__(self, cron_task_requested):
        """
        .. note::

           The cron task must be enabled to be found using this method.

        Checks to if a provided cron task id, label, or machine_label exists.

            >>> if '129da137ab9318' in self._CronTab:

        or:

            >>> if 'module.mymodule.mycron' in self._CronTab:

        :raises YomboWarning: Raised when request is malformed.
        :param cron_task_requested: The cron task ID, label, or machine_label to search for.
        :type cron_task_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(cron_task_requested)
            return True
        except:
            return False

    def __getitem__(self, cron_task_requested):
        """
        .. note::

           The cron task must be enabled to be found using this method. An alternative,
           but equal function is: :py:meth:`get() <CronTab.get>`

        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._CronTab['129da137ab9318']  #by id

        or:

            >>> off_cmd = self._CronTab['module.mymodule.mycron']  #by label & machine_label

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param cron_task_requested: The cron task ID, label, or machine_label to search for.
        :type cron_task_requested: string
        :return: A pointer to the cron task instance.
        :rtype: instance
        """
        return self.get(cron_task_requested)

    def __setitem__(self, cron_task_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, cron_task_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter cron tasks. """
        return self.cron_tasks.__iter__()

    def __len__(self):
        """
        Returns an int of the number of cron tasks configured.

        :return: The number of cron tasks configured.
        :rtype: int
        """
        return len(self.cron_tasks)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo cron tasks library"

    def keys(self):
        """
        Returns the keys (cron task ID's) that are configured.

        :return: A list of cron task IDs. 
        :rtype: list
        """
        return list(self.cron_tasks.keys())

    def items(self):
        """
        Gets a list of tuples representing the cron tasks configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.cron_tasks.items())

    def values(self):
        return list(self.cron_tasks.values())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework.

        :param loader: A pointer to the Loader library.
        :type loader: Instance of Loader
        """
        self.cron_tasks = {}
        self.cron_task_search_attributes = ['cron_id', 'label', 'enabled']
        self.check_cron_tabs_loop = None  # a simple loop that checks all cron tabs to see if they need to run.
        self.check_cron_tabs_loop = LoopingCall(self.check_cron_tabs)

    def _start_(self, **kwargs):
        """
        Start the looping call to check for cron every minute.
        """
        now = datetime.now()
        cron_next_minute =  now - timedelta(seconds = now.second - 61)  # we always run cron near the top of the minute
        cron_start = float(cron_next_minute.strftime('%s.%f')) - float(now.strftime('%s.%f')) - 0.2

        reactor.callLater(cron_start, self.start_cron_loop)

    def _stop_(self, **kwargs):
        """
        Simply stop the cron tab from running.
        """
        if self.check_cron_tabs_loop is not None and self.check_cron_tabs_loop.running:
            self.check_cron_tabs_loop.stop()

    def start_cron_loop(self):
        """
        Start the cron task loop. This was called from _start_ in an attempt to run the loop at the top
        of every second.
        """
        self.check_cron_tabs_loop.start(60)

    def check_cron_tabs(self):
        """
        Checks to see if cron needs to run anything.
        """
        the_time = datetime(*datetime.now().timetuple()[:5])
        for task in self.cron_tasks:
            self.cron_tasks[task].check(the_time)

    def get(self, cron_task_requested, limiter=None, status=None):
        """
        Looks for a cron task by it's id and label.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find cron tasks:

            >>> self._CronTab['129da137ab9318']

        or:

            >>> self._CronTab['module.mymodule.mycron']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param cron_task_requested: The cron task ID or cron task label to search for.
        :type cron_task_requested: string
        :param limiter: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter: float
        :param status: Deafult: 1 - The status of the cron task to check for.
        :type status: int
        :return: Pointer to requested cron tab.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if cron_task_requested in self.cron_tasks:
            item = self.cron_tasks[cron_task_requested]
            if status is not None and item.status != status:
                raise KeyError("Requested cron tab found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'cron_id',
                    'value': cron_task_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': cron_task_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % cron_task_requested)
                found, key, item, ratio, others = do_search_instance(attrs, self.cron_tasks,
                                                                     self.cron_task_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found cron tab by search: {cron_id}", cron_id=key)
                if found:
                    return item
                else:
                    raise KeyError("Cron tab not found: %s" % cron_task_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (cron_task_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Advanced search, typically should use the :py:meth:`get <yombo.lib.crontab.CronTab.get>` method. 

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the cron tab to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.cron_tasks,
                               self.cron_task_search_attributes,
                               _limiter,
                               _operation)

    def new(self, crontab_callback, min=allMatch, hour=allMatch, day=allMatch,
            month=allMatch, dow=allMatch, label='', enabled=True, args=(),
            kwargs={}):
        """
        Add a new :class:`CronTask`.

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
        :param enabled: (optional, default=True) If CronTask should be enabled.
        :type enabled: bool
        :param args: (optional) Arguments to pass to "crontab_callback"
        :type args: List of arguments
        :param kwargs: (optional) Keyword arguments to pass to "crontab_callback"
        :type kwargs: Dict of arguments
        """
        newCron = CronTask(crontab_callback, min=min, hour=hour, day=day, month=month,
            dow=dow, label=label, enabled=enabled, crontab_library=self, args=args,
            kwargs=kwargs)
        self.cron_tasks[newCron.cron_id] = newCron
        return newCron

    def remove(self, cron_task_requested):
        """
        Removes a CronTask. Accepts either cron id or cron name.

        To remove a cron (note, it's a method not a dictionary):
        
            >>> self._CronTab.remove('7s453hhxl3')  #by cron id

        or::

            >>> self._CronTab.remove('module.YomboBot.MyCron')  #by label

        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param cron_task_requested: The cron task id or cron label
        :type cron_task_requested: string
        """
        crontask = self.get(cron_task_requested)
        crontask.disable()
        del self.cron_tasks[crontask.cron_id]

    def enable(self, cron_task_requested):
        """
        Enable a CronTask. Accepts either cron id or cron name.

        To enable a cron (note, it's a method not a dictionary):
            >>> self._CronTab.enable('7s453hhxl3')  #by cron id
        or::
            >>> self._CronTab.enable('module.YomboBot.MyCron')  #by label

        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param cron_task_requested: The cron task id or label
        :type cron_task_requested: string
        """
        crontask = self.get(cron_task_requested)
        crontask.enable()

    def disable(self, cron_task_requested):
        """
        Disable a CronTask. Accepts either cron id or cron name.

        To disable a cron (note, it's a method not a dictionary):
            >>> self._CronTab.disable('7s453hhxl3')  #by cron id
        or::
            >>> self._CronTab.disable('module.YomboBot.MyCron')  #by label

        :param cron_task_requested: The cron task id or label
        :type cron_task_requested: string
        """
        crontask = self.get(cron_task_requested)
        crontask.disable()

    def status(self, cron_task_requested):
        """
        Get the status of a cron task. Accepts either cron id or cron name.

        To disable a cron (note, it's a method not a dictionary):
            >>> self._CronTab.disable('7s453hhxl3')  #by cron id
        or::
            >>> self._CronTab.disable('module.YomboBot.MyCron')  #by name

        :param cron_task_requested: The cron task id or label
        :type cron_task_requested: string
        """
        crontask = self.get(cron_task_requested)
        crontask.disable()

    def run_now(self, cron_task_requested):
        """
        Runs a CronTask now. Accepts either cron id or cron name.

        To run a cron (note, it's a method not a dictionary):
            >>> self._CronTab.run_now('7s453hhxl3')  #by cron id
        or::
            >>> self._CronTab.run_now('module.YomboBot.MyCron')  #by name

        :param cron_task_requested: The cron task id or label
        :type cron_task_requested: string
        """
        crontask = self.get(cron_task_requested)
        crontask.run_now()

    def set_label(self, cron_task_requested, label):
        """
        Set job label. Accepts either cron id or cron name.

        To set a label for a cron job:
            >>> self._CronTab.set_label('7s453hhxl3', 'modules.mymodule.mycrontask')  #by cron label

        :raises YomboCronTabError: Raised when cron job cannot be found.
        :param cron_task_requested: The cron task id
        :type cron_task_requested: string
        :param label: New label for cron job.
        :type label: string
        """
        crontask = self.get(cron_task_requested)
        crontask.label = label

    def run_at(self, crontab_callback, timestring, label='', args=(), kwargs={}):
        """
        Helper function for CronTab.new(), should not be called externally.

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
        :param enabled: (optional, default=True) If CronTask should be enabled.
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


class CronTask(object):
    """
    Individual cron task job, can be used to control the cron task.
    """
    def __init__(self, crontab_callback, min=allMatch, hour=allMatch, day=allMatch,
                       month=allMatch, dow=allMatch, label='',
                       enabled=True, crontab_library=None, args=(), kwargs={}):
        """
        Setup the cron event.
        """
        self.crontab_library = crontab_library
        self.cron_id = random_string(length=10)
        self.crontab_callback = crontab_callback
        self.mins = conv_to_set(min)
        self.hours = conv_to_set(hour)
        self.days = conv_to_set(day)
        self.months = conv_to_set(month)
        self.dow = conv_to_set(dow)
        self.label = label
        self.enabled = enabled
        self.args = args
        self.kwargs = kwargs

    def __del__(self):
        """
        About to delete myself.  Going to disable myself and tell crontab about this
        if it's linked.
        """
        self.enabled = False
        if self.crontab_library is not None:
          self.crontab_library.remove(self.cron_id)

    def enable(self):
        """
        Enable this CronTask.
        """
        self.enabled = True

    def disable(self):
        """
        Disable this CronTask.
        """
        self.enabled = False

    def status(self):
        """
        Returns the status of the cron task. If enabled, return True, otherwise returns False.

        :return: Status of cron task.
        :rtype: bool
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
        """"
        Called by the parent to see if the cron needs to run. This function should not be
        called externally.

        :param t: Current time in a format for the cron task.
        :return: None
        """
        if self.enabled is True and self.match_time(t):
            self.crontab_library._Statistics.increment("lib.crontab.jobs", bucket_size=15, anon=True)
            self.crontab_callback(*self.args, **self.kwargs)

    def run_now(self):
        """
        Run the cron task now.

        :return: None
        """
        self.crontab_callback(*self.args, **self.kwargs)
