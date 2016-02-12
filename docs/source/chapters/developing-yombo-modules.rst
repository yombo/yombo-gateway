###################
Developing Modules
###################

Extending the Yombo Gateway is easy! There are two demo modules and an empty
module to get you started.

The example modules will guide you through the key concepts:

* :ref:`Empty <emptymodule>` - This module is the bare minimum needed to function. Copy
  this module as a base for your own.
* :ref:`LogReader <logreader>` - Demonstrates using the Yombo filereader to
  monitor a file for reading. It also demonstrates sending device command
  :ref:`messages <message>` when valid voice command is found in a file.
* :ref:`LogWriter <logwriter>` - Demonstrates subscribing to all messages in a gateway. This
  module logs everything it receives to a file.
* :ref:`AutomationExample <automationexample>` - Demonstrates adding rules to the automation system.
* :ref:`AutomationHelpers <automationhelpers>` - Demonstrates extending the automation using various hooks.
* A more complex example that performs various activities based on time of day is documented at Yombo Projects:
  `Building Your First Module <https://projects.yombo.net/projects/modules/wiki/Building_your_first_module>`_

.. rubric:: Other Topics

* :ref:`Hooks <hooks>` - System to extend the gateway software feature set.

.. rubric:: List of demo modules

.. toctree::
   :maxdepth: 1

   ../examples/empty
   ../examples/logreader
   ../examples/logwriter
   ../examples/mynightmode
   ../examples/automationexample


