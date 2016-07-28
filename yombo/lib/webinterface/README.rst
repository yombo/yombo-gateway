============
WebInterface
============

This directory contains resources required to run the gateway web interface.

The web interface is a friendly method to get a gateway setup and running.  There are two modes:

1) Run - The gateway is working and operating as normal.
2) Config - The gateway cannot startup due to missing or invalid configuration. This mode places the
   gateway in mode that it allows it to be configured.

The web interface uses jinja2 to create html pages.

config_pages
-------------
Web pages specific to configuration run mode

fragments
-------------
Bit and pieces that make up a web page. Used by jinja2 to render HTML pages.

pages
-------------
Web pages to be displayed to user. Uses the fragements folder to create entire pages.

static
----------
A place where the browser can load static pages. Usually CSS, font, JS.
