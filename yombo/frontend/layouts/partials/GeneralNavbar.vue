<template>
  <navbar :show-navbar="showMenu" type="info" :transparent="false" position="relative">
   <div class="navbar-wrapper">
     <div class="navbar-toggle" :class="{toggled: showMenu}">
       <navbar-toggle-button @click.native="toggleNavbar">
       </navbar-toggle-button>
     </div>
     <nuxt-link class="navbar-brand" :to="localePath('index')">Yombo Gateway</nuxt-link>
   </div>

   <template slot="navbar-menu">

     <li class="nav-item">
       <nuxt-link :to="localePath('controltower')" class="nav-link">{{ $t('ui.navigation.control_tower') }}</nuxt-link>
     </li>

     <li class="nav-item">
       <nuxt-link :to="localePath('dashboard-devices')" class="nav-link">{{ $t('ui.navigation.dashboard') }}</nuxt-link>
     </li>

     <li class="nav-item">
       <nuxt-link :to="localePath('about')" class="nav-link">{{ $t('ui.navigation.about') }}</nuxt-link>
     </li>

     <li class="nav-item">
      <drop-down tag="div" title="More..." position="right">
       <nuxt-link :to="localePath('lock')" class="dropdown-item">{{ $t('ui.navigation.lockscreen') }}</nuxt-link>
       <nuxt-link :to="localePath('frontend_settings')" class="dropdown-item">{{ $t('ui.navigation.frontend_settings') }}</nuxt-link>
       <nuxt-link to="/system/restart" class="dropdown-item">{{ $t('ui.navigation.restart_gateway') }}</nuxt-link>
       <nuxt-link to="/user/logout" class="dropdown-item">{{ $t('ui.navigation.logout') }}</nuxt-link>
      </drop-down>
     </li>

     <li class="nav-item">
      <drop-down tag="div" :title="$t('system.current_language')" position="right">
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
     </li>

   </template>

 </navbar>
</template>

<script>
  import { Navbar, NavbarToggleButton } from '@/components/Common';

  export default {
    components: {
      Navbar,
      NavbarToggleButton
    },
    data(){
      return {
        showMenu: true
      }
    },
   methods: {
    toggleNavbar() {
      // applies on mobile only
      document.body.classList.toggle('nav-open')
      this.showMenu = !this.showMenu
    },
    closeMenu() {
      document.body.classList.remove('nav-open')
      this.showMenu = false
    }
   }
  }
</script>

<style>
  .navbar {
    font-size: 1.2em;
    padding: 0em 0em !important;
  }
  .dropdown-menu a{
    color: #0c5460 !important;
  }

  .dropdown-lang {
    margin-top: 5px;
    margin-left: 5px;
    font-size: 0.8571em;
    /*padding-top: .0rem;*/
    /*padding-bottom: .0rem;*/
  }

</style>
