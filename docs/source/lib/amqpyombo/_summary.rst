.. index:: amqpyombo_summary

.. _amqpyombo_summary:

.. currentmodule:: yombo.lib.amqpyombo_summary

.. meta::

   :description: Handles interactions with Yombo AMQP servers. These handlers are used by the library to process requests and responses to and from the Yombo AMQP servers.
   :keywords: amqp

============================================
AMQPYombo (yombo.lib.amqpyombo)
============================================

Handles the connection to Yombo's AMQP service. This library depends on the
:ref:`AMQP <amqp_summary>`.

AMQPYombo Library
==========================================================

.. toctree::
   :maxdepth: 1

   __init__.rst

AMQPYombo Handler classes
==========================================================

Each handler is responsible for an aspect of the AMQP communication with
Yombo servers.

.. toctree::
   :maxdepth: 1

   amqpcontrol.rst
   amqphandlerbase.rst
   amqpsystem.rst

Last updated: |today|
