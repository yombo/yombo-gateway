<template>
  <navbar :show-navbar="showNavbar">
    <div class="navbar-wrapper">
      <div class="navbar-toggle" :class="{toggled: $dashboardsidebar.showDashboardSidebar}">
        <navbar-toggle-button @click.native="toggleSidebar">
        </navbar-toggle-button>
      </div>
      <template v-for="(crumb, idx) in crumbs">
        &nbsp;/&nbsp;<nuxt-link :to="localePath({name: crumb.path, params: crumb.params})" class="simple-text logo-normal">{{$t(crumb.text)}}</nuxt-link>
      </template>
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
              <span class="d-lg-none d-md-block">{{ $t('ui.navigation.lock') }}</span>
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
        <li class="nav-item">
          <nuxt-link class="nav-link" :to="localePath('controltower')">
            <i class="fas fa-broadcast-tower fa-lg"></i>
            <p>
              <span class="d-lg-none d-md-block">{{ $t('ui.navigation.control_tower') }}</span>
            </p>
          </nuxt-link>
        </li>
        <drop-down tag="li"
                   position="right"
                   class="nav-item"
                   icon="now-ui-icons ui-1_bell-53">

          <a class="dropdown-item" href="#">{{ $t('ui.alerts.messages.none') }}</a>
        </drop-down>
        <drop-down tag="li"
                   position="right"
                   class="nav-item"
                   icon="now-ui-icons users_single-02">
          <nuxt-link class="dropdown-item" :to="localePath('dashboard')">{{ $t('ui.navigation.dashboard') }}</nuxt-link>
          <nuxt-link class="dropdown-item" :to="localePath('global_items')">{{ $t('ui.navigation.global_items') }}</nuxt-link>
          <nuxt-link class="dropdown-item" :to="localePath('frontend_settings')">{{ $t('ui.navigation.frontend_settings') }}</nuxt-link>
          <nuxt-link class="dropdown-item" :to="localePath('about')">{{ $t('ui.navigation.about') }}</nuxt-link>
          <b-dropdown-divider />
          <a class="dropdown-item" href="https://my.yombo.net">My.Yombo.Net</a>
          <b-dropdown-divider />
          <a class="dropdown-item" href="/user/logout">{{ $t('ui.navigation.logout')}}</a>
          <b-dropdown-divider />
          <nuxt-link class="dropdown-item text-danger" :to="localePath('restart')">{{ $t('ui.common.restart')}}</nuxt-link>
          <nuxt-link class="dropdown-item text-danger" :to="localePath('shutdown')">{{ $t('ui.common.shutdown')}}</nuxt-link>
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
  data: function() {
    return  {
      crumbs: [],
      activeNotifications: false,
      showNavbar: false
    };
  },
  // data: {
  //   crumbs: [],
  // },
  computed: {
    locale: function() {
      return this.$i18n.locale;
    },
  },
  methods: {
    listenerUpdateBreadcrumb(data) {
      this.crumbs.splice(data.index, 1, data);
    },
    listenerDeleteBreadcrumb(index) {
      this.crumbs.splice(index, 1);
    },
    listenerAppendBreadcrumb(data) {
      this.crumbs.push(data);
    },
    setupBreadcrumbs: function() {
      if (this.$route.path == "/") {
        return {}
      }
      let pathArray = this.$route.path.split("/");
      pathArray.shift();
      if (this.locale != "en") {
              pathArray.shift();  // remove the locale prefix from the path.
      }
      let crumbs = [];
      let path = "";
      pathArray.forEach(function(pathPart) {
        if (path.length == 0) {
          path += pathPart;
        } else {
          path += "-" + pathPart;
        }
        crumbs.push({path: path, text: "ui.navigation." + pathPart, params: {}})
      });
      this.crumbs = crumbs;
    },
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
  },
  mounted () {
    this.setupBreadcrumbs();
    this.$bus.$on('listenerUpdateBreadcrumb', e=> this.listenerUpdateBreadcrumb(e));
    this.$bus.$on('listenerDeleteBreadcrumb', e=> this.listenerDeleteBreadcrumb(e));
    this.$bus.$on('listenerAppendBreadcrumb', e=> this.listenerAppendBreadcrumb(e));
  },
  watch: {
    '$route.path': function (id) {
      this.setupBreadcrumbs();
    }
  },
};
</script>
