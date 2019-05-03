<template>
  <navbar :show-navbar="showNavbar">
    <div class="navbar-wrapper">
      <div class="navbar-toggle" :class="{toggled: $dashboardsidebar.showDashboardSidebar}">
        <navbar-toggle-button @click.native="toggleSidebar">
        </navbar-toggle-button>
      </div>
      <a class="navbar-brand" href="#">
        {{routeName}}
      </a>
    </div>
    <button @click="toggleNavbar" class="navbar-toggler" type="button" data-toggle="collapse"
            data-target="#navigation"
            aria-controls="navigation-index" aria-expanded="false" aria-label="Toggle navigation">
      <span class="navbar-toggler-bar navbar-kebab"></span>
      <span class="navbar-toggler-bar navbar-kebab"></span>
      <span class="navbar-toggler-bar navbar-kebab"></span>
    </button>

    <template slot="navbar-menu">

      <ul class="navbar-nav">
        <li class="nav-item">
          <nuxt-link class="nav-link" :to="localePath('lock')">
            <i class="fas fa-lock" style="font-size: 18px"></i>
            <p>
              <span class="d-lg-none d-md-block">Lock</span>
            </p>
          </nuxt-link>
        </li>
        <li class="nav-item">
          <nuxt-link class="nav-link" :to="localePath('index')">
            <i class="fas fa-home" style="font-size: 18px"></i>
            <p>
              <span class="d-lg-none d-md-block">Home</span>
            </p>
          </nuxt-link>
        </li>
        <li class="nav-item">
          <nuxt-link class="nav-link" :to="localePath('controltower')">
            <i class="fas fa-gamepad fa-lg"></i>
            <p>
              <span class="d-lg-none d-md-block">Control Tower</span>
            </p>
          </nuxt-link>
        </li>
        <li class="nav-item">
          <nuxt-link class="nav-link" :to="localePath('dashboard')">
            <i class="fas fa-chart-line fa-lg"></i>
            <p>
              <span class="d-lg-none d-md-block">Control Tower</span>
            </p>
          </nuxt-link>
        </li>
        <drop-down tag="li"
                   position="right"
                   class="nav-item"
                   icon="now-ui-icons ui-1_bell-53">

          <a class="dropdown-item" href="#">{{ $t('ui.alerts.messages.none')}}</a>
        </drop-down>
        <drop-down tag="li"
                   position="right"
                   class="nav-item"
                   icon="now-ui-icons users_single-02">

          <a class="dropdown-item" href="https://my.yombo.net">My.Yombo.Net</a>
          <b-dropdown-divider />
          <a class="dropdown-item" href="/user/logout">{{ $t('ui.navigation.logout')}}</a>
        </drop-down>

      </ul>

    </template>
  </navbar>
</template>
<script>
import { Navbar, NavbarToggleButton } from '@/components/Common';
import { RouteBreadCrumb } from '@/components/Dashboard';
import { CollapseTransition } from 'vue2-transitions';

export default {
  components: {
    RouteBreadCrumb,
    Navbar,
    NavbarToggleButton,
    CollapseTransition
  },
  computed: {
    routeName() {
      const { name } = this.$route;
      // console.log("routename");
      return this.capitalizeFirstLetter(name);
    }
  },
  data() {
    return {
      activeNotifications: false,
      showNavbar: false
    };
  },
  methods: {
    capitalizeFirstLetter(string) {
      return string.charAt(0).toUpperCase() + string.slice(1);
    },
    toggleNotificationDropDown() {
      this.activeNotifications = !this.activeNotifications;
    },
    closeDropDown() {
      this.activeNotifications = false;
    },
    toggleSidebar() {
      this.$dashboardsidebar.displayDashboardSidebar(!this.$dashboardsidebar.showDashboardSidebar);
    },
    toggleNavbar() {
      this.showNavbar = !this.showNavbar;
    },
    hideSidebar() {
      this.$dashboardsidebar.displayDashboardSidebar(false);
    }
  }
};
</script>
<style>
</style>
