###################
Developing Modules
###################

Extending the Yombo Gateway is easy! Full documentation is located at
`Yombo.Net - Module Development <https://yombo.net/docs/modules>`_.

An :ref:`empty <emptymodule>` module is included with the gateway to get you quickly started. Simply make a copy
of the empty module to use a framework.

Some additional reference modules for examples:

* :ref:`LogReader <logreader>` - Demonstrates using the Yombo filereader to
  monitor a file for reading.
* :ref:`LogWriter <logwriter>` - Demonstrates subscribing to all messages in a gateway. This
  module logs everything it receives to a file.
* :ref:`AutomationExample <automationexample>` - Demonstrates adding rules to the automation system.
* :ref:`AutomationHelpers <automationhelpers>` - Demonstrates extending the automation using various hooks.
* A more complex example that performs various activities based on time of day is documented at Yombo Projects:


.. rubric:: Other Topics

* :ref:`Hooks <hooks>` - System to extend the gateway software feature set.

.. rubric:: List of demo modules

.. toctree::
   :maxdepth: 1

   hooks.rst
   ../examples/empty
   ../examples/logreader
   ../examples/logwriter
   ../examples/mynightmode
   ../examples/automationexample


