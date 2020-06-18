.. index:: nodes_summary

.. _nodes_summary:

.. currentmodule:: yombo.lib.nodes

.. meta::
   :description: Maintains list of device commands available.
   :keywords: device commands, python api

==========================================================
Nodes (yombo.lib.authkeys)
==========================================================

Nodes are used to storage various data itmes. They can be used by both libraries and
modules.

Nodes Library
==========================================================

.. toctree::
   :maxdepth: 1

   __init__.rst

Node class
==========================================================

Represents a single device command.

.. toctree::
   :maxdepth: 1

   node.rst

Platform classes
==========================================================

Nodes platforms extend the capabilities of the base node type. Modules can also extend
node types by creating a directory called 'nodes' and adding class files from there, like
device type and input types.

.. toctree::
   :maxdepth: 1

   platforms/scene.rst

Last updated: |today|
