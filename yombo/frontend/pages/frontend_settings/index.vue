<template>
  <section class="container-fluid">
    <portal to="topnavbar">
      {{ $t('ui.navigation.frontend_settings') }}
    </portal>
    <div class="row justify-content-center">
      <div class="col-sm-12 col-md-10 mx-auto">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                {{ $t('ui.navigation.frontend_settings') }}
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Configuration items</p>
            </div>
            <p>
              Yombo Frontend Vue application settings.
              <br>
              <strong>Note:</strong>These setting only affect this <strong>this</strong> browser for
              <strong>this</strong> user.
            </p>
            <p>
              Lock Code:<br>
              <input v-model="newLockCode" type="password" placeholder="Set passcode" value="newLockCode">
            </p>
            <p>
              Lock Code Hint:<br>
              <input v-model="newLockCodeHint" type="text" placeholder="To tickle your brain" value="newLockCodeHint">
            </p>
            <button type="button" class="btn btn-round btn-primary active" v-on:click="saveSettings">
              {{ $t('ui.common.save') }}
            </button>
          </card>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  head() {
    return {
      title: 'Frontend Settings',
    }
  },
  data () {
    return {
      metaPageTitle: this.$t('ui.navigation.frontend_settings'),
          newLockCode: "        ",  // Save a new lock code
          newLockCodeHint: this.$store.state.frontend.settings.lockScreenPasswordHint,  // Save a new lock code
          gwLabel: null
        }
    },
  computed: {
    systemInfo: function () {
      return this.$store.state.systeminfo;
    },
  },
    methods: {
      saveSettings: function() {
        if (this.newLockCode !== "        ") {
          console.log(`saving new lock codE: ${this.newLockCode}`);
          this.$store.commit('frontend/settings/screenLockPassword', this.newLockCode);
        }
        this.$store.commit('frontend/settings/screenLockPasswordHint', this.newLockCodeHint);
        this.$swal({
          title: 'Settings saved',
          text: `Frontend settings saved.`,
          icon: 'success',
          confirmButtonClass: 'btn btn-success btn-fill',
          buttonsStyling: false
        });
      }
    },
  created: function () {
      this.$store.dispatch('gateway/systeminfo/refresh');
  },
}
</script>
