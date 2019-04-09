
<template>
  <section class="container">
    <div class="row">
      <div class="col-md-8">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                About
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Yombo Gateway Frontend</p>
            </div>
            <p>
              This website is being hosted by the <a href="https://yombo.net" target="_blank">Yombo Gateway</a>
              and is used to manage the gateway and any connected automation devices within the
              gateway cluster.
            </p>
            <p>
              The <router-link to="/dashboard">dashboard</router-link> is used for managing the
              gateway, while the <router-link to="/controltower">control tower</router-link> is
              used to manage the devices within the gateway.
            </p>
          </card>
      </div>
      <div class="col-md-4">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h3 class="card-title">
                Gateway info
              </h3>
            </div>
            <ul style="padding: 0 15px;">
              <li>Label: <strong>{{ systemInfo.label }}</strong></li>
              <li>Description: <strong>{{ systemInfo.description }}</strong></li>
              <li>DNS Name: <strong>{{ systemInfo.dns_name }}</strong></li>
              <li>Is Master: <strong>{{ systemInfo.is_master }}</strong></li>
              <li>Version: <strong>{{ systemInfo.version }}</strong></li>
              <li>Running Since: <strong>{{ systemInfo.running_since }}</strong></li>
            </ul>
          </card>
      </div>
    </div>
  </section>
</template>

<script>
export default {
    head() {
        return {
            title: 'About Gateway',
            meta: [
                { name: 'description', content: 'This is my about description here.'},
                { name: 'keywords', content: 'about nuxt, nuxt info'},
            ]
        }
    },
    data () {
          return {
              gwLabel: null
          }
      },
    computed: {
      pageTitle: function () {
        return this.gwLabel + " Home";
      },
      systemInfo: function () {
        return this.$store.state.systeminfo;
      },
      randomBGNumber : function(){
        return Math.floor(Math.random() * (10 - 1 + 1)) + 1;
      }
    },
    created: function () {
      if (this.gwLabel == null) {
        console.log("pages/index: created");
        this.$store.dispatch('systeminfo/fetch');
        // this.getSystemInfo()
      }
    },
}
</script>
