<template>
  <section class="container">
    <div class="row">
      <div class="col-md-12">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Page not found
              </h2>
            </div>
            <p>
              It looks like a bad link was followed.
            </p>
            <p>
              Popular links:
            </p>
            <ul>
              <li><nuxt-link :to="localePath('controltower')">{{$t("ui.navigation.control_tower")}}</nuxt-link></li>
              <li><nuxt-link :to="localePath('dashboard')">{{$t("ui.navigation.dashboard")}}</nuxt-link></li>
            </ul>
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
            title: 'About Yombo Frontend',
        }
    },
}
</script>
