.. index:: logreader

.. _logreader:

.. currentmodule:: yombo.modules.logreader

This module demonstrates two features of the Yombo Gateway:

1. Using the pre-made FileReader to open a file for reading. The FileReader opens
  the file in a non-blocking style and sends new lines back to the module.
  The FileReader also keeps track of where it left off between restarts so
  duplicate lines are not sent. It's smart enough to start at the top if the
  file is smaller than were it left off before.
  
2. Treats the incoming logfile as a stream of commands. This provides a simple method to allow
   other processes to trigger actions.

For more on developing modules, visit
`Projects.Yombo.net <https://projects.yombo.net/projects/modules/wiki>`_ .

==========================================
Empty Module (yombo.modules.logreader)
==========================================
.. automodule:: yombo.modules.logreader

Empty  Class
============================
.. autoclass:: logreader
   :members:
   :member-order: bysource
   :private-members:

