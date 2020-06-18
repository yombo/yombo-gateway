<template>
  <section class="container">
    <portal to="topnavbar">
      {{ metaPageTitle }}
    </portal>
    <div class="row">
      <div class="col-md-12">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                DevMode
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Cannot redirect</p>
            </div>
            <p>
              The feature or option you requested is not possible while running the Frontend Vue application in
              development mode. This mode is commonly used during development of the frontend application after
              running 'yarn run dev'.
            </p>
            <p>
              For more details, see:
              <a href="https://yombo.net/docs/frontend/development">yombo.net/docs/frontend/development</a>
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
    data() {
      return {
        metaPageTitle: "Development",
        gwLabel: null
      }
    },
    created: function () {
      // this.$store.dispatch('gateway/systeminfo/refresh');
    },
  }
</script>
