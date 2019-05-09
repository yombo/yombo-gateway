<template>
  <n-button @click.native="handleDisable()"
            class="enable"
            type="success"
            size="sm" round icon>
    <i class="fa fa-power-off"></i>
  </n-button>
</template>

<script>
export default {
  name: 'action-disable',
  props: {
    dispatch: String,
    id: String,
    i18n: String,
    item_label: String,
  },
  methods: {
    handleDisable() {
      this.$swal({
        title: this.$t('ui.prompt.disable_' + this.i18n),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, disable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch(this.dispatch, this.id);
          this.$swal({
            title: this.$t('ui.common.disabled'),
            text: `You disabled ${this.item_label}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
  }
};
</script>
<style>
</style>
