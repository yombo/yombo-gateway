/**
 * Setup the core environment variables. Also, download live data on startup and
 * periodically poll for new data. The polling to be removed after MQTT is complete.
 */
import Vue from 'vue'

// element ui language configuration
import lang from 'element-ui/lib/locale/lang/en';
import locale from 'element-ui/lib/locale';
locale.use(lang);

import VueTemperatureFilter from 'vue-temperature-filter';
// Add Global Configuration
Vue.use(VueTemperatureFilter, {
  fromFahrenheit: true,
  showText: true
});

import extend from '~/util/extend-vue-app'
import GatewayApiV1 from '@/services/gwapiv1/GatewayApiV1'
import {GetGWV1Client} from '@/services/gwapiv1/GatewayApiV1Axios'
import YomboApiV1 from '@/services/yboapiv1/YomboApiV1'
import {GetYomboV1Client} from '@/services/yboapiv1/YomboApiV1Axios'

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export default async function ({ app }, inject) {
	extend(app, {
    data: function data() {
      return {
        periodicUpdateInterval: null,
      };
    },
    async created () {
      // These context items are set within the store/index.js file when the frontend starts.
      let nuxt_env = app.context.gateway_nuxt_env
      this.$store.commit('nuxtenv/set', nuxt_env);
      this.$store.commit('gateway/systeminfo/SET_DATA', app.context.gateway_system_info);

      Object.defineProperty(process.env, 'gwenv', {value: nuxt_env, writable: true});

      // Setup Axios gateway API client.
      Object.defineProperty(Vue.prototype, '$gwenv', {value: nuxt_env, writable: true});
      Object.defineProperty(Vue.prototype, '$gwapiv1', { value: GatewayApiV1, writable: true });
      Object.defineProperty(Vue.prototype, '$gwapiv1axios', { value: GetGWV1Client(nuxt_env), writable: true });

      Object.defineProperty(Vue.prototype, '$yboapiv1', { value: YomboApiV1, writable: true });
      Object.defineProperty(Vue.prototype, '$yboapiv1axios', { value: GetYomboV1Client(app.context.user_access_token.access_token), writable: true });
      delete app.context.gateway_nuxt_env;
      delete app.context.gateway_system_info;
      this.$store.commit('gateway/access_token/SET_DATA', app.context.user_access_token);

      delete app.context.user_access_token;

    },
    methods: {
      async periodicUpdate(forceFetch = false) {
        let fetchType = "refresh";
        let multiplier = 50;  // If refreshing, lets be gentle on the client and server.
        if (forceFetch)
          fetchType = "fetch";
          multiplier = 2

        await this.$store.dispatch(`gateway/systeminfo/${fetchType}`);
        await sleep(50*multiplier);
        await this.$store.dispatch(`gateway/dashboard_navbar_items/${fetchType}`);
        await sleep(100*multiplier);
        await this.$store.dispatch(`gateway/devices/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/atoms/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/states/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/locations/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/gateways/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/commands/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/globalitems_navbar_items/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/categories/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/authkeys/${fetchType}`);
        await sleep(200*multiplier);
        await this.$store.dispatch(`gateway/roles/${fetchType}`);
      }
    },
    async beforeMount() {
      this.periodicUpdate(true);
      this.periodicUpdateInterval = setInterval(function () {
        this.periodicUpdate();
      }.bind(this), 120000);
    },
    beforeDestroy: function() {
      clearInterval(this.periodicUpdateInterval);
    }
	})
}
