
<template>
  <section class="container">
    <div class="row">
      <div class="col-md-10 mx-auto">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Frontend Settings
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Various app settings</p>
            </div>
            <p>
              Below are various settings that are local to <strong>this</strong> instance of the front-end application.
            </p>
            <p>
              Form items here:
            </p>
            <ul>
              <li>Nothing yet.</li>
            </ul>
            <p>
              Below are various frontend settings that follow this user within the current gateway cluster.
            </p>
            <p>
              Form items here:
            </p>
            <ul>
              <li>User lock pin.</li>
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
