/**
 * All items loaded here will be globally available within the app.
 */
import Vue from 'vue'

// Notifications plugin. Used on Notifications page
import Notifications from '@/components/Common/NotificationPlugin';
// Validation plugin used to validate forms
import * as VeeValidate from 'vee-validate';
// A plugin file where you could register global components used across the app
import GlobalComponents from './globalComponents';
// A plugin file where you could register global directives
import GlobalDirectives from './globalDirectives';
// Sidebar on the right. Used as a local plugin in DashboardLayout.vue
import DashboardSideBar from '@/components/Dashboard/DashboardSidebarPlugin';


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

Vue.use(GlobalComponents);
Vue.use(GlobalDirectives);
Vue.use(DashboardSideBar);
Vue.use(Notifications);
Vue.use(VeeValidate, { fieldsBagName: 'veeFields' });
