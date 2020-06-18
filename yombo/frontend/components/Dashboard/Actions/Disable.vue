<template>
  <span>
    <template v-if="size == 'small'">
      <n-button @click.native="handleDisable()"
                class="enable"
                type="success"
                size="sm" round icon>
        <i class="fa fa-power-off"></i>
      </n-button>
    </template>
    <template v-else>
      <n-button @click.native="handleDisable()"
                class="enable"
                type="success"
                size="sm">
        {{ $t('ui.common.disable') }}
      </n-button>
    </template>
  </span>

</template>

<script>
export default {
  name: 'action-disable',
  props: {
    dispatch: String,
    id: String,
    i18n: String,
    item_label: String,
    size: { type: String, default: "small"},
  },
  methods: {
    handleDisable() {
      this.$swal({
        title: `${this.$t('ui.common.disable')} ${this.$t('ui.common.' + this.i18n).toLowerCase()}? <br> ${this.item_label}`,
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        icon: 'warning',
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
            text: `${this.$t('ui.common.disabled')} ${this.$t('ui.common.' + this.i18n).toLowerCase()}: ${this.item_label}`,
            icon: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
  }
};
</script>
