<template>
  <span>
    <template v-if="size == 'small'">
      <n-button @click.native="handleDelete()"
                class="remove"
                type="danger"
                size="sm" round icon>
        <i class="fa fa-times"></i>
      </n-button>
    </template>
    <template v-else>
      <n-button @click.native="handleDelete()"
                class="remove"
                type="danger"
                size="sm">
      {{ $t('ui.common.delete') }}
      </n-button>
    </template>
  </span>
</template>

<script>
export default {
  name: 'action-delete',
  props: {
    dispatch: String,
    id: String,
    i18n: String,
    item_label: String,
    size: { type: String, default: "small"},
  },
  methods: {
    handleDelete() {
      this.$swal({
        title: `${this.$t('ui.common.delete')} ${this.$t('ui.common.' + this.i18n).toLowerCase()}? <br> ${this.item_label}`,
        text: this.$t('ui.phrase.cannot_undo'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch(this.dispatch, this.id);
          this.$swal({
            title: this.$t('ui.common.deleted'),
            text: `${this.$t('ui.common.deleted')} ${this.$t('ui.common.' + this.i18n).toLowerCase()}: ${this.item_label}`,
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
