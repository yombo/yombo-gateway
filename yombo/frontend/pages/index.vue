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
                Yombo Gateway
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">{{ systemInfo.label }}</p>
            </div>
              <i18n path="ui.pages.home.welcome" tag="p">
                <template v-slot:label>
                  <span> {{ systemInfo.label }} </span>
                </template>
              </i18n>
              <i18n path="ui.pages.home.dashboard" tag="p">
                <template v-slot:dashboard>
                  <span><nuxt-link :to="localePath('dashboard')">{{ $t('ui.navigation.dashboard') }}</nuxt-link></span>
                </template>
              </i18n>
              <i18n path="ui.pages.home.controltower" tag="p">
                <template v-slot:controltower>
                  <span><nuxt-link :to="localePath('controltower')">{{ $t('ui.navigation.control_tower') }}</nuxt-link></span>
                </template>
              </i18n>
              <i18n path="ui.pages.home.addtional_help" tag="p">
                <template v-slot:yombo_net_docs>
                  <span><a href="https://yombo.net/docs">Yombo.net/docs</a></span>
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
    data() {
      return {
        metaPageTitle: this.$t('ui.navigation.home'),  // also used by commonMixin to set page header
      };
    },
    components: {
      GatewayInfoCard,
    },
  }
</script>
