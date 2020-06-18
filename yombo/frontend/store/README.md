# STORE

This directory contains the Vuex Store files.
Vuex Store option is implemented in the Nuxt.js framework.

Files in this directory act like modules.

This directory is supercharged by Nuxt, see:
[Nuxt vuex store doco](https://nuxtjs.org/guide/vuex-store).

# Local Storage 

Many of the items will be stored in Local Storage on the web
browser, after being LZ compressed. This allows the frontend
application to startup quicker without forcing the user to
download all the data first.

LZ Compression is used to speed up writing the data to Local
Storage. This compression achieves around 75-85% compression.

Notes:

1) The application will automatically refresh data automatically
   on startup.
2) The application will download/refresh data as needed as the user
   navigates through the application.

# ORM

Vuex ORM (https://github.com/vuex-orm/vuex-orm) is used to access
and manipulate data. Be sure to follow this standard as much as
possible for consistency.
