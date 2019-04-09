<template>
  <section class="container">
    <div class="row">
      <div class="col-md-8">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Yombo Gateway
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">{{ systemInfo.label }}</p>
            </div>
            <p>
              Welcome to the Yombo Gateway Frontend. Use the <nuxt-link to="/dashboard">Dashboard</nuxt-link>
              to manage the gateway, including any automation devices, rules, and scenes.
            </p>
            <p>
              Additionally, use the <nuxt-link to="/controltower">Control Tower</nuxt-link> as a control
              display for all your automation devices.
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
            title: this.systemInfo.label + ": Yombo Gateway",
            meta: [
                { name: 'description', content: 'Yombo Gateway: ' + this.systemInfo.description},
                { name: 'keywords', content: 'yombo, gateway, frontend'},
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
    methods: {
    }
  }
  // https://www.thepolyglotdeveloper.com/2018/04/vuejs-app-using-axios-vuex/
</script>
