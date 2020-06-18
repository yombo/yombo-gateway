# Yombo Frontend

This directory contains the frontend application that is used to manage the gateway
and control devices.

This application was written using the following components:
 
* Vue
* Nuxt
* Bootstrap
* See package.json for additional components

# Usage

Visit the url for the gateway, such as http://example.yombo.me or
http://localhost:8080.

# Compilation

The front end requires yarn installed on the system to order to compile the frontend
application. If you used the automated setup scripts or images, such as Yombian
for Raspberry PI, the **gateway will automatically recompile as needed.**
Due to the heavy processing required, this may take a few minutes for the application
to finish compiling.

A base application comes already compiled and ready to go when the gateway is distributed,
however, any additional modules added to the gateway will require the frontend application
to be recompiled, which wil be handled automatically.

# Development

To help with rapid development, yarn can be used to compile and run a local webserver
on port 3000. To start the development environment, open a shell prompt and type the
following commands:

``` bash
# Change to the frontend directory:
$ cd /opt/yombo-gateway/yombo/frontend
$ yarn run dev
```

First, you need to be authenticated with Yombo. First, visit the Frontend application
(either your dynamic DNS name or http://localhost:8080). After logging in, then visit 
visit the website at: http://localhost:3000

It's recommended to use Chrome with the Vue extension installed and enabled. This will
provide additional debug information inside Chrome developer tools.

# Build for production

Once you are done tinkering with development and wish to see it working, run the
following command to compile and distribute the source code:

``` bash
# Change to the front directory:
$ cd /opt/yombo-gateway/yombo/frontend
$ yarn run prod
```

This will build the production version of the application (smaller code & faster),
and then it will copy the files to the correct locations.

# Additional links

* [Vue.js](https://vuejs.org/) - The core application framework
* [Nuxt.js](https://nuxtjs.org) - Built on top of Vue and extends the framework. Adds several
  layout components. Look here first instead of the boostrap docs. This also handles automatic
  route setup, vuex, vue-route, and more.
* [Bootstrap](https://getbootstrap.com/docs/4.3/getting-started/introduction/) - Bootstrap
  layout documentation.
