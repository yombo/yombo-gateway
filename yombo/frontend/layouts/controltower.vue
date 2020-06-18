<template>
  <div style="min-height: 100vh;">
    <notifications></notifications>
    <div>
      <basic-top-navbar>
      </basic-top-navbar>
      <router-view name="header"></router-view>
      <div class="panel-header panel-header-sm">
      </div>
        <!-- your content here -->
        <nuxt />
    </div>
  </div>
</template>

<script>
  import BasicTopNavbar from '@/layouts/ControlTower/TopNavbar.vue';

  export default {
    components: {
      BasicTopNavbar,
    },
    computed: {
      bgImageNumber: function () {
        return Math.floor(new Date()/10000) % 5;
      },
      bgImageSize: function() {
        // console.log(this.$root.$data.window.width);
        if (this.$root.$data.window.width <= 600) {
          return 600;
        } else if (this.$root.$data.window.width <= 1364) {
          return 1364;
        } else {
          return 2048;
        }
      },
      systemInfo: function () {
        return this.$store.state.gateway.systeminfo;
      },
      imageUrl: function() {
        let protocol = location.protocol;
        let slashes = protocol.concat("//");
        let host = slashes.concat(window.location.hostname);
        let url = new URL(host);
        url.port = this.$store.state.nuxtenv.internal_http_port;
        return url.toString()
      }
    }

  }
</script>
