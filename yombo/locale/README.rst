=====================
Locales Directory
=====================

Stores frontend and backend translation files.

Backend
========
This is used by the system to translate system messages, which may or may not be displayed in
the frontend. These are typically used for the log files, and other types of events.

When the Yombo Gateway loads, it merges any language files supplied by modules, if any.
These are stored in the user's working directory, usually:
~/.yombo/locale/LC_MESSAGES

These files are formatted in the .po syntax. These are managed through lokalise:
https://lokalise.co/public/708239755b345a901b2e41.78129082/

Frontend
========
This used by the frontend build process and is not managed by the Yombo Gateway software.

The build process merges the files located in this directory along with any modules that
have the ./locale/frontend directory with the correctly formatted json files.

These files are formatted in the .json syntax. These are managed through lokalise:
https://lokalise.co/public/974982865b3422bf9a2177.49453396/
