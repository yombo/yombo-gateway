<template>
  <div slot="footer" class="stats">
    <i v-on:click="refreshRequest" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
    {{$t('ui.common.updated')}} {{display_age}}
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
      display_age: 'Unkown',
    }
  },
  methods: {
    async refreshRequest() {
      this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.mesages.refreshing_data'),
          type: 'success',
          showConfirmButton: true,
          timer: 1000
      });
      await this.$store.dispatch(this.refresh);
      this.updateDataAge();
    },
    updateDataAge () { // called by setInterval setup in mounted()
      this.display_age = this.$store.getters[this.getter](this.$i18n.locale);
    },
  },
  mounted() {
    this.updateDataAge();
    this.$options.interval = setInterval(this.updateDataAge, 5000);
    console.log("last updated mounted....")
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },

};
</script>
<style>
</style>
