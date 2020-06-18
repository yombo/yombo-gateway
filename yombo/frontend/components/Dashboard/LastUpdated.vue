<template>
  <div slot="footer" class="stats">
    <i v-on:click="refreshRequest" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
    {{display_age}}
  </div>
</template>

<script>
export default {
  name: 'last-updated',
  props: {
    refresh: String,
    getter: String,
  },
  data() {
    return {
      display_age: 'Unknown',
    }
  },
  methods: {
    async refreshRequest() {
      this.$swal({
        title: this.$t('ui.modal.titles.on_it'),
        text: this.$t('ui.modal.messages.refreshing_data'),
        icon: 'success',
        showConfirmButton: false,
        timer: 1200
      });
      await this.$store.dispatch(this.refresh);
      this.updateDataAge();
    },
    updateDataAge () { // called by setInterval setup in mounted()
      let display_age = this.$store.getters[this.getter](this.$i18n.locale);
      if (display_age == "never") {
        this.display_age = this.$t("ui.relative_time.never_downloaded");
      } else {
        this.display_age = this.$t('ui.common.updated') + " " + this.$t("ui.relative_time.past", {time: display_age});
      }
    },
  },
  mounted() {
    this.updateDataAge();
    this.$options.interval = setInterval(this.updateDataAge, 1000);
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },

};
</script>
