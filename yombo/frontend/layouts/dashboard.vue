<template>
  <div class="wrapper" :class="{'nav-open': $dashboardsidebar.showDashboardSidebar}">
    <notifications></notifications>
    <dashboard-side-bar>
      <template slot-scope="props" slot="links">
        <dashboard-sidebar-item :link="{name: 'Dashboard', icon: 'fas fa-home', path: '/dashboard'}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.devices'), icon: 'fas fa-wifi'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.list'), path: localePath('dashboard-devices')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.add'), path: localePath('dashboard-devices-add')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.common.discovered'), path: localePath('dashboard-devices-discovered')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.automation'), icon: 'fas fa-random'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.rules'), path: localePath('dashboard-automation-rules')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.scenes'), path: localePath('dashboard-automation-scenes')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.crontab'), path: localePath('dashboard-automation-crontab')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.info'), icon: 'fas fa-info'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.atoms'), path: localePath('dashboard-atoms')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.device_commands'), path: localePath('dashboard-device_commands')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.intents'), path: localePath('dashboard-intents')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.states'), path: localePath('dashboard-states')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.storage'), path: localePath('dashboard-storage')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.statistics'), icon: 'fas fa-tachometer-alt', path: localePath('dashboard-statistics')}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.permissions'), icon: 'fas fa-user-shield'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.roles'), path: localePath('dashboard-permissions-roles')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.users'), path: localePath('dashboard-permissions-users')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.settings'), icon: 'fas fa-cogs'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.locations'), path: localePath('dashboard-locations')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.areas'), path: localePath('dashboard-areas')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.dns'), path: localePath('dashboard-settings-dns')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.encryption'), path: localePath('dashboard-settings-encryption')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.gateways'), path: localePath('dashboard-gateways')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.yombo_ini'), path: localePath('dashboard-settings-yomboini')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'MQTT', icon: 'far fa-envelope'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.send'), path: localePath('dashboard-mqtt')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.monitor'), path: localePath('dashboard-mqtt-monitor')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.system'), icon: 'fas fa-download'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.overview'), path: localePath('dashboard-system-overview')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.backup'), path: localePath('dashboard-system-backup')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.debug'), path: localePath('dashboard-system-debug')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.http_event_stream'), path: localePath('dashboard-system-http_event_stream')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.events'), path: localePath('dashboard-system-events')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.status'), path: localePath('dashboard-system-status')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.web_logs'), path: localePath('dashboard-permissions-webinterface_logs')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.debug'), icon: 'fas fa-bug'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.overview'), path: localePath('dashboard-debug')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.authentication_platforms'), path: localePath('dashboard-debug-authentication_platforms')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.cache'), path: localePath('dashboard-debug-cache')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.commands'), path: localePath('dashboard-debug-commands')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.device_types'), path: localePath('dashboard-debug-device_types')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.events'), path: localePath('dashboard-debug-events')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.hooks_called_libraries'), path: localePath('dashboard-debug-hooks_called_libraries')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.hooks_called_modules'), path: localePath('dashboard-debug-hooks_called_modules')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.modules'), path: localePath('dashboard-debug-modules')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.nodes'), path: localePath('dashboard-debug-nodes')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.sslcerts'), path: localePath('dashboard-debug-sslcerts')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.statistic_bucket_lifetimes'), path: localePath('dashboard-debug-statistic_bucket_lifetimes')}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.requirements'), path: localePath('dashboard-debug-requirements')}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

      </template>
    </dashboard-side-bar>
    <div class="main-panel">
      <top-navbar></top-navbar>
      <router-view name="header"></router-view>
  <div class="panel-header panel-header-sm">
  </div>
      <div :class="{content: !$route.meta.hideContent}" @click="toggleSidebar">
        <zoom-center-transition :duration="150" mode="out-in">
          <!-- your content here -->
          <router-view></router-view>
        </zoom-center-transition>
      </div>
      <content-footer v-if="!$route.meta.hideFooter"></content-footer>
    </div>
  </div>
</template>

<script>
/* eslint-disable no-new */
import PerfectScrollbar from 'perfect-scrollbar';
import 'perfect-scrollbar/css/perfect-scrollbar.css';

function hasElement(className) {
  return document.getElementsByClassName(className).length > 0;
}

function initScrollbar(className) {
  if (hasElement(className)) {
    new PerfectScrollbar(`.${className}`);
  } else {
    // try to init it later in case this component is loaded async
    setTimeout(() => {
      initScrollbar(className);
    }, 100);
  }
}

import TopNavbar from '@/layouts/Dashboard/TopNavbar.vue';
import ContentFooter from '@/layouts/Dashboard/ContentFooter.vue';
import DashboardContent from '@/layouts/Dashboard/Content.vue';
import MobileMenu from '@/layouts/Dashboard/Extra/MobileMenu.vue';
import { SlideYDownTransition, ZoomCenterTransition } from 'vue2-transitions';

export default {
  components: {
    TopNavbar,
    ContentFooter,
    DashboardContent,
    MobileMenu,
    // UserMenu,
    SlideYDownTransition,
    ZoomCenterTransition
  },
  methods: {
    toggleSidebar() {
      if (this.$dashboardsidebar.showDashboardSidebar) {
        this.$dashboardsidebar.displayDashboardSidebar(false);
      }
    }
  },
  mounted() {
    let docClasses = document.body.classList;
    let isWindows = navigator.platform.startsWith('Win');
    if (isWindows) {
      // if we are on windows OS we activate the perfectScrollbar function
      initScrollbar('sidebar');
      initScrollbar('sidebar-wrapper');

      docClasses.add('perfect-scrollbar-on');
    } else {
      docClasses.add('perfect-scrollbar-off');
    }
  }
};
</script>
<style lang="scss">
$scaleSize: 0.95;
@keyframes zoomIn95 {
  from {
    opacity: 0;
    transform: scale3d($scaleSize, $scaleSize, $scaleSize);
  }
  to {
    opacity: 1;
  }
}
.main-panel .zoomIn {
  animation-name: zoomIn95;
}
@keyframes zoomOut95 {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: scale3d($scaleSize, $scaleSize, $scaleSize);
  }
}
.main-panel .zoomOut {
  animation-name: zoomOut95;
}
</style>
