.. index:: webinterface_summary

.. _webinterface_summary:

.. currentmodule:: yombo.lib.webinterface


=======================================
WebInterface (yombo.lib.webinterface)
=======================================

Provides web interface to the Yombo Gateway. Useful for setting up the gateway and
interacting with th Yombo API.

The web interface is broken down into several modules. See below for the core module functions.

See the `Web Interface library documentation <https://yombo.net/docs/libraries/web_interface>`_ for more
details.

Web Interface Library
=========================

The Webinterface library has been broken down to multiple files for easier
management.

.. toctree::
   :maxdepth: 1

   __init__.rst
   mixins/frontend_mixin.rst
   mixins/load_routes_mixin.rst
   mixins/render_mixin.rst
   mixins/webserver_mixin.rst

Routes
=======

Route files handle various URLs for the Web Interface library. Currently, the
documentation system is unable to automatically generate easily viewable
documentation. Please view the
`source code for the routes <https://github.com/yombo/yombo-gateway/tree/master/yombo/lib/webinterface/routes>`_ .

Additionally, see the :ref:`LoadRoutesMixin <wi_load_routes_mixin>` for list of route files
loaded.

Web Interface HTML
==================

The HTML pages displayed can be viewed from the git repository:

  * `HTML Pages <https://github.com/yombo/yombo-gateway/tree/master/yombo/lib/webinterface/pages>`_
  * `Fragrments <https://github.com/yombo/yombo-gateway/tree/master/yombo/lib/webinterface/fragments>`_

Helper Files
============

.. toctree::
   :maxdepth: 1

   auth.rst
   response_tools.rst
   yombo_site.rst

Last updated: |today|
