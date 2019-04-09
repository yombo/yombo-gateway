<template>
  <div class="dashboard-sidebar"
       :data-color="backgroundColor">

    <div class="logo">
      <nuxt-link to="/" class="simple-text logo-mini">
        <div class="logo-image">
          <img :src="logo">
        </div>
      </nuxt-link>

      <nuxt-link to="/" class="simple-text logo-normal">
        {{title}}
      </nuxt-link>
      <div class="navbar-minimize">
        <button id="minimizeDashboardSidebar" class="btn btn-simple btn-icon btn-neutral btn-round" @click="minimizeDashboardSidebar">
          <i class="now-ui-icons text_align-center visible-on-dashboard-sidebar-regular"></i>
          <i class="now-ui-icons design_bullet-list-67 visible-on-dashboard-sidebar-mini"></i>
        </button>
      </div>
    </div>
    <div class="dashboard-sidebar-wrapper" ref="dashboard-sidebarScrollArea">
      <slot></slot>
      <ul class="nav">
        <slot name="links">
          <dashboard-sidebar-item v-for="(link, index) in dashboardsidebarLinks"
                        :key="link.name + index"
                        :link="link">

            <dashboard-sidebar-item v-for="(subLink, index) in link.children"
                          :key="subLink.name + index"
                          :link="subLink">
            </dashboard-sidebar-item>
          </dashboard-sidebar-item>
        </slot>

      </ul>
    </div>
  </div>
</template>
<script>
export default {
  name: 'dashboard-sidebar',
  props: {
    title: {
      type: String,
      default: 'Yombo'
    },
    backgroundColor: {
      type: String,
      default: 'black',
      validator: value => {
        let acceptedValues = [
          '',
          'blue',
          'azure',
          'green',
          'orange',
          'red',
          'purple',
          'black'
        ];
        return acceptedValues.indexOf(value) !== -1;
      }
    },
    logo: {
      type: String,
      default: 'img/logo-100px.png'
    },
    dashboardsidebarLinks: {
      type: Array,
      default: () => []
    },
    autoClose: {
      type: Boolean,
      default: true
    }
  },
  provide() {
    return {
      autoClose: this.autoClose
    };
  },
  methods: {
    minimizeDashboardSidebar() {
      if (this.$dashboardsidebar) {
        this.$dashboardsidebar.toggleMinimize();
      }
    }
  },
  beforeDestroy() {
    if (this.$dashboardsidebar.showDashboardSidebar) {
      this.$dashboardsidebar.showDashboardSidebar = false;
    }
  }
};
</script>
<style>
@media (min-width: 992px) {
  .navbar-search-form-mobile,
  .nav-mobile-menu {
    display: none;
  }
}
</style>
