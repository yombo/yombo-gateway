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
                {{ $t('ui.common.restart') }}
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Yombo Gateway Service</p>
            </div>
            <p>
              Restart the gateway? <br>
              <nuxt-link
                to="/">
                <button type="button" class="btn btn-round btn-secondary active">{{ $t('ui.common.cancel') }}</button>
              </nuxt-link>
              <a href="/system/restart" class="btn btn-round btn-danger" role="button" aria-pressed="true">
                {{ $t('ui.common.restart') }}</a>
            </p>

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
        metaPageTitle: this.$t('ui.common.restart'),
      };
    },
    created: function () {
      console.log(`about created, root: ${this.$root.ive_data}`)
      this.$store.dispatch('gateway/systeminfo/refresh');
    }
}
</script>
