<template>
    <section class="container">
    <div class="row">
      <div class="col-md-12">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Control Tower
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Device Control</p>
            </div>
            <p>
              The control tower will allow you to easily control devices and see their status.
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
            title: 'Control Tower',
            meta: [
                { name: 'description', content: 'This is my about description here.'},
                { name: 'keywords', content: 'about nuxt, nuxt info'},
            ]
        }
    }
}
</script>

<style>
</style>
