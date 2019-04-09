
<template>
  <section class="container">
    <div class="row">
      <div class="col-md-10 mx-auto">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Gateway Locked
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Yombo Gateway Frontend</p>
            </div>
            <p>
              This gateway has been locked.  Enter passcode below to unlock.
            </p>
            <p>
              ...A form goes here...
            </p>
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
