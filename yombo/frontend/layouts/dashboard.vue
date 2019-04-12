<template>
  <div class="wrapper" :class="{'nav-open': $dashboardsidebar.showSidebar}">
    <notifications></notifications>
    <dashboard-side-bar>
      <template slot-scope="props" slot="links">
        <dashboard-sidebar-item :link="{name: 'Dashboard', icon: 'fas fa-home', path: '/dashboard'}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'Devices', icon: 'fas fa-wifi'}">
          <dashboard-sidebar-item :link="{name: 'List', path: '/dashboard/devices'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Add', path: '/dashboard/devices/add'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Discovered', path: '/dashboard/devices/discovered'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'Automation', icon: 'fas fa-random'}">
          <dashboard-sidebar-item :link="{name: 'Rules', path: '/dashboard/automation/rules'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Scenes', path: '/dashboard/automation/scenes'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'CronTab', path: '/dashboard/automation/crontab'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'Info', icon: 'fas fa-info'}">
          <dashboard-sidebar-item :link="{name: 'Atoms', path: '/dashboard/atoms'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Device Commands', path: '/dashboard/device_commands'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Intents', path: '/dashboard/intents'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'States', path: '/dashboard/states'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Storage', path: '/dashboard/storage'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'Statistics', icon: 'fas fa-tachometer-alt', path: '/dashboard/statistics'}">
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'Permissions', icon: 'fas fa-user-shield'}">
          <dashboard-sidebar-item :link="{name: 'Roles', path: '/dashboard/permissions/roles'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Users', path: '/dashboard/permissions/users'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'Settings', icon: 'fas fa-cogs'}">
          <dashboard-sidebar-item :link="{name: 'Locations', path: '/dashboard/locations'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'DNS', path: '/dashboard/settings/dns'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Encryption', path: '/dashboard/settings/encryption'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Gateways', path: '/dashboard/settings/gateways'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Yombo.Ini', path: '/dashboard/settings/yomboini'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'MQTT', icon: 'far fa-envelope'}">
          <dashboard-sidebar-item :link="{name: 'Send', path: '/mqtt/send'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Monitor', path: '/mqtt'}"></dashboard-sidebar-item>
        </dashboard-sidebar-item>

        <dashboard-sidebar-item :link="{name: 'System', icon: 'fas fa-download'}">
          <dashboard-sidebar-item :link="{name: 'Overview', path: '/dashboard/system/overview'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Backup', path: '/dashboard/system/backup'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Debug', path: '/dashboard/system/debug'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'HTTP Event Stream', path: '/dashboard/system/http_event_stream'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Events', path: '/dashboard/system/events'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Status', path: '/dashboard/system/status'}"></dashboard-sidebar-item>
          <dashboard-sidebar-item :link="{name: 'Web Logs', path: '/dashboard/permissions/webinterface_logs'}"></dashboard-sidebar-item>
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
