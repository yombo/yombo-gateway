<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.label.edit_device') }}: {{item.full_label}}
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
                {{ $t('ui.label.delete') }}
            </n-button>
          </div>
         </h4>
        </div>
        <div class="card-body">
          Device: {{id}}
          {{item}}
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import Device from '@/models/device'

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
      return Device.find(this.id)
    },
  },

  methods: {
    handleDelete(row) {
      this.$swal({
        title: this.$t('ui.prompt.delete_device'),
        text: this.$t('ui.phrase.cannot_undo'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch('yombo/devices/delete', row.id);
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
        title: this.$t('ui.prompt.enable_device'),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'info',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('yombo/devices/enable', row.id);
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
        title: this.$t('ui.prompt.disable_device'),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, disable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('yombo/devices/disable', row.id);
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

  },
  mounted () {
    this.$store.dispatch('yombo/devices/fetchOne', this.id);
  },
};
</script>
