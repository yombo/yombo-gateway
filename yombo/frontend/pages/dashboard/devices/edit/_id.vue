<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.navigation.edit_device') }}
         </h4>
        </div>
        <div class="card-body">
          Device:
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { Table, TableColumn } from 'element-ui';
import _ from 'lodash';

import Device from '@/models/device'

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn
  },
  data() {
    return {
      search: '',
      display_age: '0 seconds',
    };
  },
  computed: {
    device () {
      return Device.find()
    },
  },

  methods: {
    handleDelete(index, row) {
      this.$swal({
        title: 'Are you sure?',
        text: `You won't may not be able to revert this!`,
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch('devices/delete', row.id);
          this.$swal({
            title: 'Deleted!',
            text: `You deleted ${row.full_name}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
    async handleEnable(index, row) {
      await this.$swal({
        title: 'Are you sure?',
        text: `This will enable the device, the gateway may need to be rebooted.`,
        type: 'info',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('devices/enable', row.id);
          console.log('Enabled status: ' + JSON.stringify(results))
          this.$swal({
            title: 'Enabled!',
            text: `You enabled ${row.full_name}`,
            type: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
    async handleDisable(index, row) {
      await this.$swal({
        title: 'Are you sure?',
        text: `This will disable the device, the gateway may need to be rebooted.`,
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('devices/disable', row.id);
          console.log('Enabled status: ' + JSON.stringify(results))
          this.$swal({
            title: 'Enabled!',
            text: `You enabled ${row.full_name}`,
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
      this.$store.dispatch('devices/fetch');
    },
    refresh() { // called by debounceRefreshed if the user hasn't clicked on refresh too often.
      this.$store.dispatch('devices/refresh');
    },
    updateDeviceAge () { // called by setInterval setup in mounted()
      this.display_age =  this.$store.getters['devices/display_age'](this.$i18n.locale);
    },
    device_updated(updated_at) { // called by bus.$on setup in mounted()
      this.updateDeviceAge();
      console.log("Devices were updated: " + updated_at);
    }

  },
  created () {
    this.debouncedRefresh = _.throttle(this.refresh, 5000);
    this.$store.dispatch('devices/refresh');
    this.$store.dispatch('locations/refresh');
  },
  mounted () {
    this.updateDeviceAge();
    this.$options.interval = setInterval(this.updateDeviceAge, 5000);
    this.$bus.$on('store_devices_updates', this.device_updated);
    // console.log("devices mounted....");
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
    this.$bus.$off('store_devices_updates', this.device_updated);
    // console.log("device before destroy")
  },
};
</script>

<style>
/*.table-transparent {*/
/*  background-color: transparent !important;*/
/*}*/
</style>
