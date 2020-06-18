<template>
  <div>
    <frontend-loading></frontend-loading>
    <div v-if="frontend_ready !== null">
      <style>
        body {
          background-image: url('{{ imageUrl() }}img/bg/{{bgImageNumber}}_{{bgImageSize}}.jpg?1');
          background-repeat: no-repeat;
          background-size: auto;
        }
      </style>
      <notifications></notifications>
      <div>
        <basic-top-navbar></basic-top-navbar>
        <router-view name="header"></router-view>
        <div class="panel-header panel-header-sm">
        </div>
          <!-- your content here -->
          <nuxt />
        <GeneralFooter />
      </div>
    </div>
  </div>
</template>

<script>
  import BasicTopNavbar from '@/layouts/partials/BasicTopNavbar.vue';
  import GeneralFooter from '@/layouts/partials/GeneralFooter.vue';
  import FrontendLoading from '@/components/FrontendLoading.vue';

  export default {
    components: {
      BasicTopNavbar,
      FrontendLoading,
      GeneralFooter,
    },
    computed: {
      frontend_ready () {
        return this.$store.state.nuxtenv.gateway_id;
      },
      bgImageNumber: function () {
        return Math.floor(new Date() / 10000) % 5;
      },
      bgImageSize: function () {
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
    },
    methods: {
      imageUrl() {
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

