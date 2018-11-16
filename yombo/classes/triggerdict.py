#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Allows for creation of a dictionary That will call a callback whenever the dictionary
changes.

**Usage**:

.. code-block:: python

   from yombo.classes.triggerdict import TriggerDict

   # Set a callback to be called whenever the dictionary changes.
   items = TriggerDict(200, {"mom" : "Jane", "dad" : "Joe"}, callback=self.somefunction)
   items["brother"] = "Jeff"   # add an additional entry.

   # Change the callback method
   items.set_callback(self.anotherfunction)

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""


class TriggerDict(dict):
    """
    A simple dictionary that accepts "callback" as a keywork argument that can be used to call
    a function if the dictionary changes.

    The callback can also be changed through the method "set_callback".
    """

    def __init__(self, *args, callback=None, **kwargs):
        self.callback = callback
        dict.__init__(self, *args, **kwargs)

    def __setitem__(self, item, value):
        super().__setitem__(item, value)
        if self.callback is not None:
            self.callback(item, value)

    def set_callback(self, callback):
        """
        Change the callback method.
        :param callback:
        :return:
        """
        self.callback = callback
