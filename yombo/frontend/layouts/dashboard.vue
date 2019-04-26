<template>
  <div class="wrapper" :class="{'nav-open': $dashboardsidebar.showSidebar}">
    <notifications></notifications>
    <dashboard-side-bar>
      <template slot-scope="props" slot="links">
        <dashboard-sidebar-item :link="{name: 'Dashboard', icon: 'fas fa-home', path: '/dashboard'}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.devices'), icon: 'fas fa-wifi'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.list'), path: '/dashboard/devices'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.add'), path: '/dashboard/devices/add'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.common.discovered'), path: '/dashboard/devices/discovered'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.automation'), icon: 'fas fa-random'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.rules'), path: '/dashboard/automation/rules'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.scenes'), path: '/dashboard/automation/scenes'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.crontab'), path: '/dashboard/automation/crontab'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.info'), icon: 'fas fa-info'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.atoms'), path: '/dashboard/atoms'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.device_commands'), path: '/dashboard/device_commands'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.intents'), path: '/dashboard/intents'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.states'), path: '/dashboard/states'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.storage'), path: '/dashboard/storage'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.statistics'), icon: 'fas fa-tachometer-alt', path: '/dashboard/statistics'}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.permissions'), icon: 'fas fa-user-shield'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.roles'), path: '/dashboard/permissions/roles'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.users'), path: '/dashboard/permissions/users'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.settings'), icon: 'fas fa-cogs'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.locations'), path: '/dashboard/locations'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.dns'), path: '/dashboard/settings/dns'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.encryption'), path: '/dashboard/settings/encryption'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.gateways'), path: '/dashboard/settings/gateways'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.yombo_ini'), path: '/dashboard/settings/yomboini'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'MQTT', icon: 'far fa-envelope'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.send'), path: '/mqtt/send'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.monitor'), path: '/mqtt'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: $t('ui.navigation.system'), icon: 'fas fa-download'}">
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.overview'), path: '/dashboard/system/overview'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.backup'), path: '/dashboard/system/backup'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.debug'), path: '/dashboard/system/debug'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.http_event_stream'), path: '/dashboard/system/http_event_stream'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.events'), path: '/dashboard/system/events'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.status'), path: '/dashboard/system/status'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: $t('ui.navigation.web_logs'), path: '/dashboard/permissions/webinterface_logs'}"></dashboard-sidebar-item>
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
      if (this.$dashboardsidebar.showSidebar) {
        this.$dashboardsidebar.displaySidebar(false);
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
