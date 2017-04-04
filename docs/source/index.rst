.. title:: Yombo Python API Reference

=================================
Yombo Automation Python Reference
=================================

Release v0.13.0 (`Installation <https://yombo.net/docs/gateway/getting_started/>`_)

**Yombo** automation allows easy DIY automation using an easy to web configuration interface for setup. It also
provides a way to create simple python files for advanced automation logic.

Behold the power of Yombo automation:

.. code-block:: python

    #  A simple custom module that manages the porch light.
    def _time_event_(**kwargs):
        """
        Called when a time of day event occurs.

        We turn on a porch light
        """
        event = kwargs['value']
        porch_light = self._Device['porch light']
        if (event == 'is.dusk'):
           off_time = self._Times.get_next('hour=22', 'minute'=30')

           porch_light.do_command(cmd='on')  # turn on now
           porch_light.do_command(cmd='off', not_before=off_time)  # turn of at 10:30pm

**Yombo** allows you to easily access all your devices and send commands to them in the future, Yombo handles all
the details of sending the commands thru the proper locations at the proper times.

API Documentation
=================

This site is for those who wish to tinker with writing logic to manage their automation system. For code samples
and getting started guides, visit the `Yombo Development Documentation <https://yombo.net/docs/modules>`_


Useful links
=============

* `Yombo Home <https://yombo.net/>`_
* `Installation <https://yombo.net/docs/gateway/getting_started/>`_
* `End user documentation <https://yombo.net/documents/>`_
* `Building your first module - a walk complete guide <https://yombo.net/docs/modules/building-your-first-module/>`_

Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :numbered:
   :includehidden:

   chapters/yombo-framework.rst
   chapters/developing-yombo-modules.rst

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
