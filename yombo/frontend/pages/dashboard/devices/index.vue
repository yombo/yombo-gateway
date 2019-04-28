<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="fa-pull-right">
            <a :href="localePath('dashboard-devices-add')" title="New Device" class="btn btn-info btn-sm fa-pull-right" role="button">
            <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
          <br>
           <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.label.search_ddd')"/>
          </div>
        <h4 class="card-title">
           {{ $t('ui.navigation.devices') }}
         </h4>
           <div slot="footer" class="stats">
             <i v-on:click="refreshRequest" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
             {{$t('ui.label.updated')}} {{display_age}}
           </div>
        </div>
        <div class="card-body">
          <el-table
            :data="devices.filter(data => !search
             || data.label.toLowerCase().includes(search.toLowerCase())
             || data.description.toLowerCase().includes(search.toLowerCase())
             )"
          >
            <el-table-column :label="$t('ui.label.label')" property="full_label"></el-table-column>
            <el-table-column :label="$t('ui.label.description')" property="description"></el-table-column>
            <el-table-column :label="$t('ui.label.location')" property="full_location"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.label.actions')">
              <div slot-scope="props" class="table-actions">
                <n-button @click.native="handleEdit(props.$index, props.row)"
                          class="edit"
                          type="info"
                          size="sm" round icon>
                  <i class="fa fa-edit"></i>
                </n-button>

                <template v-if="props.row.status == 1">
                  <n-button @click.native="handleDisable(props.$index, props.row)"
                            class="enable"
                            type="success"
                            size="sm" round icon>
                    <i class="fa fa-power-off"></i>
                  </n-button>
                </template>
                <template v-else>
                  <n-button @click.native="handleEnable(props.$index, props.row)"
                            class="disable"
                            type="default"
                            size="sm" round icon
                            :disabled="props.row.status == 2">
                    <i class="fa fa-power-off"></i>
                  </n-button>
                </template>

                <n-button @click.native="handleDelete(props.$index, props.row)"
                          class="remove"
                          type="danger"
                          size="sm" round icon>
                  <i class="fa fa-times"></i>
                </n-button>
              </div>
            </el-table-column>
          </el-table>
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
    devices () {
      return Device.query().with('locations').orderBy('id', 'desc').get()
    },
  },

  methods: {
    handleEdit(index, row) {
      this.$router.push(this.localePath('dashboard-devices-edit')+"/"+row.id);
    },
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
        confirmButtonText: 'Yes, disable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('devices/disable', row.id);
          console.log('Disabled status: ' + JSON.stringify(results))
          this.$swal({
            title: 'Disabled!',
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
