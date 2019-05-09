<template>
  <n-button @click.native="handleDelete()"
            class="remove"
            type="danger"
            size="sm" round icon>
    <i class="fa fa-times"></i>
  </n-button>
</template>

<script>
export default {
  name: 'action-delete',
  props: {
    dispatch: String,
    id: String,
    i18n: String,
    item_label: String,
  },
  methods: {
    handleDelete() {
      this.$swal({
        title: this.$t('ui.prompt.delete_' + this.i18n),
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
            text: `You deleted ${this.item_label}`,
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
