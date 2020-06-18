import pkg from './package';

const webpack = require('webpack');

const dateTimeFormats = {
  'en': {
    date: {
      year: 'numeric', month: 'numeric', day: 'numeric'
    },
    date_long: {
      year: 'numeric', month: 'short', day: 'numeric'
    },
    datetime: {
      year: 'numeric', month: 'numeric', day: 'numeric',
      hour: 'numeric', minute: 'numeric'
    },
    datetime_long: {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: 'numeric', minute: 'numeric'
    },
    datetime_weekday: {
      year: 'numeric', month: 'numeric', day: 'numeric',
      weekday: 'short', hour: 'numeric', minute: 'numeric'
    },
    datetime_weekday_long: {
      year: 'numeric', month: 'short', day: 'numeric',
      weekday: 'short', hour: 'numeric', minute: 'numeric'
    },
  },
};

export default {
  mode: 'spa',
  ssr: false,
  /*
  ** Headers of the page
  */
  head: {
    title: "Yombo Frontend",
    meta: [
      { charset: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { hid: 'description', name: 'description', content: pkg.description }
    ],
    script: [
      { src: 'https://use.fontawesome.com/releases/v5.13.0/js/all.js' }
    ],
    link: [
      { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
    ]
  },

  router: {
    // Run these items on every page
    middleware: [
      'lockscreen',
      'disablespa'
      ]
  },

  generate: {
    routes: [
      '/',
    ],
    fallback: false,
  },

  /*
  ** Customize the progress-bar color
  */
  loading: { color: '#fff' },

  /*
  ** Global CSS
  */
  css: [
    '@/assets/sass/dashboard.scss',
    'vue-multiselect/dist/vue-multiselect.min.css',
    'vue-loading-overlay/dist/vue-loading.css',
  ],

  /*
  ** Plugins to load before mounting the App
  */
  plugins: [
    { src: '~/plugins/bus.js', mode: 'client' },  // Global bus.
    { src: '~/plugins/localStorage.js', mode: 'client' },  // persistent data
    { src: '~/plugins/environment.js', mode: 'client' },  // Downloads env data from gateway
    { src: '~/plugins/browser.js', mode: 'client' },  // Monitor browser events - resize and language.
    { src: '~/plugins/vue-inject.js', mode: 'client' },
    { src: '~/plugins/index.js', mode: 'client' },  // Sets up global components and directives
    { src: '~/plugins/filters.js', mode: 'client' },  // Filters used within components.
    { src: '~/plugins/mixins.js', mode: 'client' },  // Filters used within components.
    { src: '~/plugins/mqtt.js', mode: 'client' },  // Adds MQTT support.
  ],

  /*
  ** Nuxt.js modules
  */
  modules: [
    'bootstrap-vue/nuxt',  // Bootstrap for vue.
    '@nuxtjs/pwa',  // Create progressive web app.
    '~modules/generate-whitelist.js',
    'nuxt-client-init-module',  // Used to download the gateway env data within store/index.js
    'vue-sweetalert2/nuxt',  // Pretty alerts
    'portal-vue/nuxt',  // Magically place data from any component to any other component
    ['nuxt-i18n', {
      seo: false,
      defaultLocale: 'en',
      detectBrowserLanguage: {
        useCookie: true,
        cookieKey: 'yombo_frontend_i18n'
      },
      locales: [
        { code: 'ar', file: 'ar.js' },
        { code: 'en', file: 'en.js' },
        { code: 'es', file: 'es.js' },
        { code: 'es_419', file: 'es_419.js' },
        { code: 'hi_IN', file: 'hi_IN.js' },
        { code: 'it', file: 'it.js' },
        { code: 'pt', file: 'pt.js' },
        { code: 'pt_BR', file: 'pt_BR.js' },
        { code: 'ru', file: 'ru.js' },
        { code: 'vi', file: 'vi.js' },
        { code: 'zh_CN', file: 'zh_CN.js' },
        { code: 'zh_TW', file: 'zh_TW.js' },
      ],
      lazy: true,
      langDir: 'lang/',
      vueI18n: {
        dateTimeFormats,
        silentTranslationWarn: true,
        fallbackLocale: 'en',
        messages: {
          en: require('./lang/en.json'),
        }
      }
    }],

  ],
  /*
  ** Axios module configuration
  */
  axios: {
    // See https://github.com/nuxt-community/axios-module#options
  },

  /*
  ** Build configuration
  */
  build: {
    /*
    * You can extend webpack config here
    *
    * This current setting forces smaller chunks together, causing the browser to make less download
    * requests.
    */
    extend(config, ctx) {
      if (!this.dev) {
        config.plugins.push(
            new webpack.optimize.MinChunkSizePlugin({
            minChunkSize: 50000
          })
        )
      }
    }
  }
}
