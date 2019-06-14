<template>
  <div class="wrapper" :class="{'nav-open': $dashboardsidebar.showDashboardSidebar}">
    <notifications></notifications>
    <dashboard-side-bar>
      <template slot-scope="props" slot="links">
        <template v-for="item in nav_items">
          <dashboard-sidebar-item :link="{name: $t(item.out.label), icon: item.out.icon, path: localePath(item.out.path)}">
            <template v-for="subitem in item.in" v-if="item.in.length > 0">
              <dashboard-sidebar-item :link="{name: $t(subitem.label),
               path: localePath({name: subitem.path.label, params: subitem.path.params })}"></dashboard-sidebar-item>
            </template>
          </dashboard-sidebar-item>
        </template>
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
          <nuxt />

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
  data: function data() {
    return {
    };
  },
  computed: {
    nav_items: function () {
      return this.$store.state.gateway.frontend_dashboard_navbar.data;
    },
    last_download_at: function () {
      return this.$store.state.gateway.frontend_dashboard_navbar.last_download_at;
    },
  },
  methods: {
    toggleSidebar() {
      if (this.$dashboardsidebar.showDashboardSidebar) {
        this.$dashboardsidebar.displayDashboardSidebar(false);
      }
    }
  },
  mounted() {
    console.log("about to get gateway frontend_dashboard_navbar")
    this.$store.dispatch('gateway/frontend_dashboard_navbar/fetch');

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
.panel-header {
  height: 10px;
  padding-top: 25px;
}

.main-panel > .content {
  padding-top: 20px;
}
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
