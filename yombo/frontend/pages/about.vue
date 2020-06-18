<template>
  <section class="container-fluid">
    <portal to="topnavbar">
      {{ metaPageTitle }}
    </portal>
    <div class="row justify-content-center">
      <div class="col-sm-7 col-md-6 col-lg-6">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                {{ $t('ui.navigation.about') }}
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Yombo Gateway Frontend</p>
            </div>
            <i18n path="ui.pages.dashboard_about.details" tag="p">
              <template v-slot:yombonet>
                <span><a href="https://yombo.net" target="_blank">Yombo</a></span>
              </template>
              <template v-slot:dashboard>
                <span><nuxt-link :to="localePath('dashboard')">{{ $t('ui.navigation.dashboard') }}</nuxt-link></span>
              </template>
            </i18n>
            <i18n path="ui.pages.dashboard_about.control_tower" tag="p">
              <template v-slot:controltower>
                <span><nuxt-link :to="localePath('controltower')">{{ $t('ui.navigation.control_tower') }}</nuxt-link></span>
              </template>
            </i18n>
          </card>
      </div>
      <div class="col-sm-5 col-md-5 col-lg-4">
        <gateway-info-card></gateway-info-card>
      </div>
    </div>
  </section>
</template>

<script>
  import GatewayInfoCard from '@/components/Misc/GatewayInfoCard.vue';

  export default {
    components: {
      GatewayInfoCard,
    },
    data() {
      return {
        metaPageTitle: this.$t('ui.navigation.about'),
      };
    },
    created: function () {
      console.log(`about created, root: ${this.$root.ive_data}`)
      this.$store.dispatch('gateway/systeminfo/refresh');
    }
}
</script>
