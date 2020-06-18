<template>
  <section class="container-fluid">
    <portal to="topnavbar">
      {{ metaPageTitle }}
    </portal>
    <div class="row">
      <div class="col-sm-12 col-md-10 mx-auto">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Screen Lock
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Yombo Gateway Frontend</p>
            </div>
            <template v-if="lockCode == null">
              <p>
                The gateway is not locked, and cannot be until a passcode has been set:
                <br>
                <input v-model="newLockCode" type="password" placeholder="Set passcode">
                <button type="button" class="btn btn-round btn-secondary active" v-on:click="setLockCode">
                  {{ $t('ui.common.save') }}
                </button>
              </p>
              <p>
                The passcode can be changed from the
                <nuxt-link :to="localePath('frontend_settings')">Frontend Settings</nuxt-link> page.
              </p>
            </template>
            <template v-else-if="locked === true">
              <p>
                This gateway has been locked.  Enter passcode below to unlock:
              </p>
              <p>
                <input v-model="enteredUnlockCode" type="password" placeholder="Enter passcode">
                <br>
                <button type="button" class="btn btn-round btn-success active" v-on:click="tryUnlock">
                  {{ $t('ui.navigation.unlock') }}
                </button>
              </p>
              <p>
                Hint: {{lockCodeHint}}
              </p>
            </template>
            <template v-else>
              <p>
                This gateway is not locked.
              </p>
              <p>
                <button type="button" class="btn btn-round btn-danger" v-on:click="lockscreen">
                  {{ $t('ui.navigation.lock') }}
                </button>
              </p>
              <p>
                The passcode can be changed from the
                <nuxt-link :to="localePath('frontend_settings')">Frontend Settings</nuxt-link> page.
              </p>
            </template>
          </card>
      </div>
    </div>
  </section>
</template>

<script>
  import { commonMixin } from '@/mixins/commonMixin';

  export default {
    mixins: [commonMixin],
    components: {
      // numkeyboard
    },
    data() {
      return {
        metaPageTitle: this.$t('ui.navigation.lock'),
        newLockCode: "",  // Save a new lock code
        lockCodeHint: this.$store.state.frontend.settings.lockScreenPasswordHint,  // Save a new lock code
        enteredUnlockCode: "", // A code entered to try to unlock
      };
    },
    computed: {
      locked () {
        return this.$store.state.frontend.settings.lockScreenLocked;
      },
      lockCode () {
        return this.$store.state.frontend.settings.lockScreenPassword;
      },
    },
    methods: {
      tryUnlock: function () {
        console.log(`${this.enteredUnlockCode} == ${this.lockCode}`)
        if (this.enteredUnlockCode === this.lockCode) {
          this.$store.commit('frontend/settings/screenLocked', false);
        } else {
          this.$swal({
            title: 'Invalid code!',
            text: `The unlock code is invalid.`,
            icon: 'error',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
        this.enteredUnlockCode = "";
      },
      lockscreen: function () {
        this.$store.commit('frontend/settings/screenLocked', true);
      },
      setLockCode: function() {
        this.$store.commit('frontend/settings/screenLockPassword', this.newLockCode);
      }
    },
    created: function () {
      this.$store.dispatch('gateway/systeminfo/refresh');
    },
  }
</script>
