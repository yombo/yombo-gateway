<template>
  <div>
    <style>
      body {
        background-image: url('{{imageUrl}}img/bg/{{bgImageNumber}}_{{bgImageSize}}.jpg');
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
</template>


<script>
  import BasicTopNavbar from '@/layouts/Dashboard/BasicTopNavbar.vue';
  import GeneralFooter from '@/layouts/partials/GeneralFooter.vue';

  export default {
    components: {
      BasicTopNavbar,
      GeneralFooter,
    },
    computed: {
      bgImageNumber: function () {
        return Math.floor(new Date()/10000) % 5;
      },
      bgImageSize: function() {
        console.log(this.$root.$data.window.width);
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
        url.port = this.systemInfo.internal_http_port;
        return url.toString()
      }
    }

  }
</script>

<style>
.panel-header {
  height: 10px;
  padding-top: 20px;
}

body {
  font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI',
    Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 16px;
  word-spacing: 1px;
  -ms-text-size-adjust: 100%;
  -webkit-text-size-adjust: 100%;
  -moz-osx-font-smoothing: grayscale;
  -webkit-font-smoothing: antialiased;
  /*box-sizing: border-box;*/
  /*background-image: url('/img/bg/1_1536.jpg');*/
    /*background-size: contain;*/
  background-repeat: no-repeat;
  -webkit-background-size: cover;
  -moz-background-size: cover;
  -o-background-size: cover;
  background-size: cover;
  background-position: right top;
  /*width: 100%;*/
  /*height: 100%;*/
  /*overflow: hidden;*/
}
*,
*:before,
*:after {
  box-sizing: border-box;
  margin: 0;
}
.button--green {
  display: inline-block;
  border-radius: 4px;
  border: 1px solid #3b8070;
  color: #3b8070;
  text-decoration: none;
  padding: 10px 30px;
}
.button--green:hover {
  color: #fff;
  background-color: #3b8070;
}
.button--grey {
  display: inline-block;
  border-radius: 4px;
  border: 1px solid #35495e;
  color: #35495e;
  text-decoration: none;
  padding: 10px 30px;
  margin-left: 15px;
}
.button--grey:hover {
  color: #fff;
  background-color: #35495e;
}
</style>
