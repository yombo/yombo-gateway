Web interface display pages
================================

Contains the pages used to display the web interface, not related to the the Frontend
Vue application. These pages are used for logging in/out, errors, or setting up
the gateway.

The HTML pages use a Jinja2 templating system to make webpages standardized and
aid in developing new pages.

Directories
================================

errors
----------------
Contains pages that display various errors

misc
------
Misc pages:

  * json_api.html - Display API data in a more friendly manor.
  * reboot_needed.html - Displayed when the gateway needs to be rebooted
  * still_building_frontend.html - Displayed when the frontend Vue app is still being built.
  * still_loading.html - Displayed when gateway core is still loading.

setup_wizard
--------------
Used when the gateway is being setup. The routes to these pages are disabled during
normal runtime.

Pages in order of usage:

  * start.html - Starting point for setting up the gateway. Prompt to setup new gateway, or
    restore from backup.
  * select_gateway.html - Select ane existing gateway or create a new one.
  * basic_settings.html - Gateway title, description, location, etc.
  * advanced_settings.html - Clustering and security options.
  * dns.html - Setup dynamic DNS.
  * finished.html - Last page, pronmpts user to reboot gateway.

user
-----
Various user pages, such as login.

Files
================================

  * blank.html - A blank page to use to create additional pages.
