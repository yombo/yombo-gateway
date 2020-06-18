<template>
  <span>
    <template v-if="this.size == 'small'">
      <n-button @click.native="handleEnable()"
                class="enable"
                type="default"
                size="sm" round icon>
        <i class="fa fa-power-off"></i>
      </n-button>
    </template>
    <template v-else>
      <n-button @click.native="handleEnable()"
                class="enable"
                type="default"
                size="sm">
      {{ $t('ui.common.enable') }}
      </n-button>
    </template>
  </span>
</template>

<script>
export default {
  name: 'action-enable',
  props: {
    dispatch: String,
    id: String,
    i18n: String,
    item_label: String,
    size: { type: String, default: "small"},
  },
  methods: {
    handleEnable() {
      console.log(this.item_label)
      this.$swal({
        title: `${this.$t('ui.common.enable')} ${this.$t('ui.common.' + this.i18n).toLowerCase()}? <br> ${this.item_label}`,
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        icon: 'question',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch(this.dispatch, this.id);
          this.$swal({
            title: this.$t('ui.common.enabled'),
            text: `${this.$t('ui.common.enabled')} ${this.$t('ui.common.' + this.i18n).toLowerCase()}: ${this.item_label}`,
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
