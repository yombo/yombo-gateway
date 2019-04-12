/**
 * All items loaded here will be globally available within the app.
 */
import Vue from 'vue'

// Notifications plugin. Used on Notifications page
import Notifications from '@/components/Common/NotificationPlugin';
// Validation plugin used to validate forms
import VeeValidate from 'vee-validate';
// A plugin file where you could register global components used across the app
import GlobalComponents from './globalComponents';
// A plugin file where you could register global directives
import GlobalDirectives from './globalDirectives';
// Sidebar on the right. Used as a local plugin in DashboardLayout.vue
import DashboardSideBar from '@/components/Dashboard/DashboardSidebarPlugin';
// import DashboardSideBar from '@/plugins/DashboardSidebarPlugin';

// element ui language configuration
import lang from 'element-ui/lib/locale/lang/en';
import locale from 'element-ui/lib/locale';
locale.use(lang);

export default {
  install(Vue) {
  }
};

import axios from 'axios'

async function getEnv() {
  let response = await axios.get('/nuxt.env');
  if (typeof response.data === 'string') {
    console.log("response data is a string....");
    console.log(response.data);
    console.log(JSON.parse(response.data));
    Object.defineProperty(Vue.prototype, '$gwenv', {value: JSON.parse(response.data)});
  } else {
    Object.defineProperty(Vue.prototype, '$gwenv', {value: response.data});
  }
}

getEnv();

import GatewayApiV1 from '@/services/gwapiv1/GatewayApiV1'
Object.defineProperty(Vue.prototype, '$gwapiv1', { value: GatewayApiV1 });

import YomboApiV1 from '@/services/yboapiv1/YomboApiV1'
Object.defineProperty(Vue.prototype, '$yboapiv1', { value: YomboApiV1 });

Vue.use(GlobalComponents);
Vue.use(GlobalDirectives);
Vue.use(DashboardSideBar);
Vue.use(Notifications);
Vue.use(VeeValidate, { fieldsBagName: 'veeFields' });
