.. title:: Yombo Python API Reference

=================================
Yombo Automation Python Reference
=================================

Release v0.13.0 (`Installation <https://docs.yombo.net/Gateway/Getting_started>`_)

Python API Documentation
========================

This site is for those who wish to tinker with writing logic to manage their automation system. For code samples
and getting started guides, visit the `Yombo Development Documentation <https://docs.yombo.net/Developing_modules>`_

Overview
========

**Yombo** automation allows simple DIY automation. Setup and configuration is completed using a browser
instead of getting lost in complicated text files.

The true power of the system comes from building simple modules that even non-programmers can write. These
are simple python files that nearly anyone can write.  This example turns on a porch light when it's dusk
and turns it off at 10:30pm:

.. code-block:: python

    #  A simple custom module that manages the porch light.
    def _time_event_(**kwargs):
        """
        Called when a time of day event occurs.
        """
        event = kwargs['value']  # Can be 'now_light', 'now_twilight', 'now_not_dawn', etc.
        if (event == 'now_dusk'):
           porch_light = self._Device['porch light']
           porch_light.command(cmd='on')  # turn on now

           off_time = self._Times.get_next('hour=22', 'minute'=30')  # get epoch for the next 10:30pm time.
           porch_light.command(cmd='off', not_before=off_time)  # turn of at 10:30pm

Useful links
=============

* `Yombo Home <https://yombo.net/>`_
* `Installation <https://docs.yombo.net/Gateway/Getting_started>`_
* `End user documentation <https://docs.yombo.net/>`_
* `Building your first module - a walk complete guide <https://docs.yombo.net/Developing_modules/Building_your_first_module>`_


Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :numbered:
   :includehidden:

   chapters/useful-links.rst
   chapters/yombo-framework.rst
   chapters/developing-yombo-modules.rst
   chapters/license.rst

Contributing to Developer Documentation
========================================

The Yombo Gateway uses self documenting code. All documentation found on this website is generated directly from
the `source code itself <https://github.com/yombo/yombo-gateway>`_.

Making changes is easy: simply find the section of the code and update the code comment. This website is periodically
updated from the source code.

.. rubric:: Index and search

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. rubric:: License Information

:Homepage: https://yombo.net/
:Copyright: 2013-2017 Yombo
:License: For the open source license, see the LICENSE file

Last updated: |today|
