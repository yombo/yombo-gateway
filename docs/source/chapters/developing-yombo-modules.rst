###################
Developing Modules
###################

Developing modules for the Yombo Gateway framework is made easier with the
help of three example modules, and an empty starter module.

The example modules will guide you through the key concepts:

* :ref:`Empty <emptymodule>` - This module is the bare minimum needed to function.
* :ref:`LogReader <logreader>` - Demonstrates using the Yombo filereader to
  monitor a file for reading. It also demonstrates sending device command
  :ref:`messages <message>` when valid voice command is found in a file.
  :ref:`LogWriter <logwriter>` - Demonstrates subscribing to all messages. This
  module logs everything it receives to a file.
* :ref:`Mynightmode <mynight>` - The demo module outlined in the
  `Building Your First Module <https://projects.yombo.net/projects/modules/wiki/Building_you_first_module>`_
  wiki article. (Still under development)

.. toctree::
   :maxdepth: 1

   ../examples/empty
   ../examples/logreader
   ../examples/logwriter
   ../examples/mynightmode
