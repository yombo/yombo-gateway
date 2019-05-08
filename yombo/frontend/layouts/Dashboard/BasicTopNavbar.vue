<template>
  <navbar :show-navbar="showNavbar">
    <div class="navbar-wrapper">
      <nuxt-link class="nav-link" :to="localePath('index')">Yombo Gateway</nuxt-link>
    </div>
    <template slot="navbar-menu">

      <ul class="navbar-nav">
        <li class="nav-item">
          <nuxt-link class="nav-link" :to="localePath('about')">
            <i class="fas fa-question" style="font-size: 18px"></i>
            <p>
              <span class="d-lg-none d-md-block">Lock</span>
            </p>
          </nuxt-link>
        </li>
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
          <nuxt-link class="dropdown-item" :to="localePath('frontend_settings')">Frontend Settings</nuxt-link>
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
  }
};
</script>
<style>
</style>
