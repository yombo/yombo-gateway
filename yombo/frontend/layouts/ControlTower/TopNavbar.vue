<template>
  <navbar :show-navbar="showNavbar">
    <div class="mr-1">
      <nuxt-link :to="localePath('controltower')">{{ $t('ui.navigation.control_tower') }}</nuxt-link>
      &nbsp;/&nbsp;
    </div>
    <portal-target name="topnavbar" />
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
              <span class="d-lg-none d-md-block">{{ $t('ui.navigation.home') }}</span>
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
          <nuxt-link class="dropdown-item" :to="localePath('controltower')">{{ $t('ui.navigation.control_tower') }}</nuxt-link>
          <nuxt-link class="dropdown-item" :to="localePath('dashboard')">{{ $t('ui.navigation.dashboard') }}</nuxt-link>
          <nuxt-link class="dropdown-item" :to="localePath('frontend_settings')">{{ $t('ui.navigation.frontend_settings') }}</nuxt-link>
          <nuxt-link class="dropdown-item" :to="localePath('about')">{{ $t('ui.navigation.about') }}</nuxt-link>
          <b-dropdown-divider />
          <a class="dropdown-item" href="https://my.yombo.net">My.Yombo.Net</a>
          <b-dropdown-divider />
          <a class="dropdown-item" href="/user/logout">{{ $t('ui.navigation.logout')}}</a>
        </drop-down>

        <drop-down tag="li"
                   position="right"
                   class="nav-item"
                   icon="fas fa-globe fa-lg">
          <nuxt-link :to="switchLocalePath('ar')" class="dropdown-lang"> العربية</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('en')" class="dropdown-lang"><span class="flag-icon flag-icon-us"></span>English</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('es')" class="dropdown-lang">Español</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('es_419')" class="dropdown-lang">Español - LA</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('hi_IN')" class="dropdown-lang"> हिन्दी</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('it')" class="dropdown-lang">Italiano</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('pt')" class="dropdown-lang">Rortuguês</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('pt_BR')" class="dropdown-lang">Português - BR</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('ru')" class="dropdown-lang">Русский язык</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('vi')" class="dropdown-lang">Tiếng Việt</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('zh_CN')" class="dropdown-lang">中文 (Simplified)</nuxt-link><br>
          <nuxt-link :to="switchLocalePath('zh_TW')" class="dropdown-lang">中文 (Traditional)</nuxt-link><br>
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
    toggleNavbar() {
      this.showNavbar = !this.showNavbar;
    },
    closeDropDown() {
      this.activeNotifications = false;
    },
  }
};
</script>
