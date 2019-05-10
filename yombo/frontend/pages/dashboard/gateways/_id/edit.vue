<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.common.edit_gateway') }}: {{item.label}}
          <div class="pull-right">
            <template v-if="item.status == 1">
              <n-button @click.native="handleDisable(item)"
                        class="enable"
                        type="warning"
                        size="sm">
                {{ $t('ui.common.disable') }}
              </n-button>
            </template>
            <template v-else>
              <n-button @click.native="handleEnable(item)"
                        class="disable"
                        type="success"
                        size="sm"
                        :disabled="item.status == 2">
                {{ $t('ui.common.enable') }}
              </n-button>
            </template>
            <n-button @click.native="handleDelete(item)"
                      class="remove"
                      type="danger"
                      size="sm">
                {{ $t('ui.common.delete') }}
            </n-button>
          </div>
         </h4>
        </div>
        <div class="card-body">
          Gateway: {{id}}
          {{item}}
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import Gateway from '@/models/gateway'

export default {
  layout: 'dashboard',
  components: {
  },
  data() {
    return {
      id: this.$route.params.id,
      display_age: '0 seconds',
    };
  },
  computed: {
    item () {
      return Gateway.find(this.id)
    },
  },

  methods: {
    handleDelete(row) {
      this.$swal({
        title: this.$t('ui.prompt.delete_gateway'),
        text: this.$t('ui.phrase.cannot_undo'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch('yombo/gateways/delete', row.id);
          this.$swal({
            title: this.$t('ui.common.deleted'),
            text: `You deleted ${row.full_name}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
    async handleEnable(row) {
      await this.$swal({
        title: this.$t('ui.prompt.enable_gateway'),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'info',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('yombo/gateways/enable', row.id);
          this.$swal({
            title: this.$t('ui.common.enabled'),
            text: `You enabled ${row.full_name}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
    async handleDisable(row) {
      await this.$swal({
        title: this.$t('ui.prompt.disable_gateway'),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, disable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('yombo/gateways/disable', row.id);
          this.$swal({
            title: this.$t('ui.common.disabled'),
            text: `You disabled ${row.full_name}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },

    tableRowClassName({ rowIndex }) {
      if (rowIndex === 0) {
        return 'table-success';
      } else if (rowIndex === 2) {
        return 'table-info';
      } else if (rowIndex === 4) {
        return 'table-danger';
      } else if (rowIndex === 6) {
        return 'table-warning';
      }
      return '';
    },
    refreshRequest() {
      this.debouncedRefresh();
      this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.mesages.refreshing_data'),
          type: 'success',
          showConfirmButton: true,
          timer: 1000
      });
      this.$store.dispatch('yombo/gateways/refresh');
    },
    refresh() { // called by debounceRefreshed if the user hasn't clicked on refresh too often.
      this.$store.dispatch('yombo/gateways/refresh');    },

  },
  mounted () {
    this.$store.dispatch('yombo/gateways/fetchOne', this.id);
  },
};
</script>

<style>
/*.table-transparent {*/
/*  background-color: transparent !important;*/
/*}*/
</style>
