<template>
  <div class="stats">
    <span v-on:click="refreshRequest"><i class="fas fa-sync" style="color: #14375c;"></i></span>
    <span v-on:click="refreshRequest" v-if="displayAgePath">{{displayAge}}</span>
  </div>
</template>

<script>
  export default {
    name: 'data-last-updated',
    props: {
      displayAgePath: String,
      dashboardFetchData: Function,
      refreshPath: String,
    },
    data() {
      return {
        displayAge: 'Unknown',
      }
    },
    methods: {
      refreshRequest() {
        console.log("refresh request starting..");
        console.log(this);
        console.log(this.$swal);
        this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.messages.refreshing_data'),
          icon: 'success',
          showConfirmButton: false,
          timer: 1200
        });
        if (this.dashboardFetchData != null) {
          this.dashboardFetchData()
        } else if (this.refreshPath != null) {
          this.$store.dispatch(this.refreshPath)
            .then(function() {
              if (this.displayAgePath != null) this.updateDataAge();
            });
        }
      },
      updateDataAge () { // called by setInterval setup in mounted()
        if (this.displayAgePath == null) return;
        let displayAge = this.$store.getters[this.displayAgePath](this.$i18n.locale);
        if (displayAge == "never") {
          this.displayAge = this.$t("ui.relative_time.never_downloaded");
        } else {
          this.displayAge = this.$t('ui.common.updated') + " " + this.$t("ui.relative_time.past", {time: displayAge});
        }
      },
    },
    mounted() {
      if (this.dashboardFetchData != null || this.refreshPath != null) {
        this.updateDataAge();
        this.$options.interval = setInterval(this.updateDataAge, 1000);
      }
    },
    beforeDestroy () {
      if (this.dashboardFetchData != null || this.refreshPath != null) {
        clearInterval(this.$options.interval);
      }
    },
  };
</script>
