import pkg from './package'

export default {
  mode: 'spa',
  ssr: false,
  /*
  ** Headers of the page
  */
  head: {
    title: pkg.name,
    meta: [
      { charset: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { hid: 'description', name: 'description', content: pkg.description }
    ],
    script: [
      { src: 'https://use.fontawesome.com/releases/v5.8.1/js/all.js' }
    ],
    link: [
      { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
    ]
  },

  router: {
    // Run the middleware/user-agent.js on every page
    middleware: 'disablespa'
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
    '@/assets/css/custom.css',
  ],

  /*
  ** Plugins to load before mounting the App
  */
  plugins: [
    { src: '~/plugins/index.js', ssr: false },
    { src: '~/plugins/localStorage.js', ssr: false },
    { src: '~/plugins/startup.js', ssr: false },
  ],

  /*
  ** Nuxt.js modules
  */
  modules: [
    // // Doc: https://axios.nuxtjs.org/usage
    // '@nuxtjs/axios',
    // Doc: https://bootstrap-vue.js.org/docs/
    'bootstrap-vue/nuxt',
    '@nuxtjs/pwa',
    'vue-sweetalert2/nuxt',
    ['nuxt-i18n', {
      seo: false,
      // locales: ['en', 'fr', 'es'],
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
         fallbackLocale: 'en',
         messages: {
           en: require('./lang/en.json'),
         }
       }
      }
    ],

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
    ** You can extend webpack config here
    */
    extend(config, ctx) {
    }
  }
}
