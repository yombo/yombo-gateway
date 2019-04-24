<template>
  <navbar :show-navbar="showMenu" type="info" :transparent="false" position="relative">
   <div class="navbar-wrapper">
     <div class="navbar-toggle" :class="{toggled: showMenu}">
       <navbar-toggle-button @click.native="toggleNavbar">
       </navbar-toggle-button>
     </div>
     <nuxt-link class="navbar-brand" to="/">Yombo Gateway</nuxt-link>
   </div>

   <template slot="navbar-menu">

     <li class="nav-item">
       <nuxt-link to="/controltower" class="nav-link">
         Control Tower
       </nuxt-link>
     </li>

     <li class="nav-item">
       <nuxt-link to="/dashboard" class="nav-link">
         Dashboard
       </nuxt-link>
     </li>

     <li class="nav-item">
       <nuxt-link to="/about" class="nav-link">
         About
       </nuxt-link>
     </li>

     <li class="nav-item">
      <drop-down tag="div" title="More..." position="right">
       <nuxt-link to="/lock" class="dropdown-item">Lock Screen</nuxt-link>
       <nuxt-link to="/frontend_settings" class="dropdown-item">Frontend Settings</nuxt-link>
       <nuxt-link to="/system/restart" class="dropdown-item">Restart Gateway</nuxt-link>
       <nuxt-link to="/user/logout" class="dropdown-item">Logout</nuxt-link>
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
</style>
