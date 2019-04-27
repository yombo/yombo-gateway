<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
         <h4 class="card-title">
           {{ $t('ui.navigation.devices') }}
            <a href="#/devices/add" title="New Device" class="btn btn-info btn-sm fa-pull-right" role="button">
            <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
         </h4>
           <div v-on:click="refreshRequest" slot="footer" class="stats">
             <i class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i> Updated {{data_age}} seconds ago.
           </div>

        </div>
        <el-table
          :data="devices.filter(data => !search
           || data.label.toLowerCase().includes(search.toLowerCase())
           || data.description.toLowerCase().includes(search.toLowerCase())
           )"
        >
          <el-table-column label="Label" property="full_label"></el-table-column>
          <el-table-column  label="Description" property="description"></el-table-column>
          <el-table-column  label="Location" property="full_location"></el-table-column>
          <el-table-column
            align="right">
            <template slot="header" slot-scope="scope">
              <el-input
                v-model="search"
                size="mini"
                placeholder="Type to search"/>
            </template>
            <template slot-scope="scope">
              EDIT DELETE
            </template>
          </el-table-column>
        </el-table>
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
      data_age: 0,
    };
  },
  computed: {
    devices () {
      return Device.query().with('locations').orderBy('id', 'desc').get()
    },
    last_download_at () {
      return this.$store.state.devices.last_download_at
    },
  },

  methods: {
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
    updateDeviceAge () {
      this.data_age = (new Date(Date.now()/1000)) - this.$store.state.devices.last_download_at;
    }
  },
  created () {
    // this.$bus.$on('messageSent', e => console.log("DB:devices: " + e));
    this.debouncedRefresh = _.throttle(this.refresh, 5000);
    this.$store.dispatch('devices/refresh');
    this.$store.dispatch('locations/refresh');
  },
  mounted () {
    this.$options.interval = setInterval(this.updateDeviceAge, 1000);
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
};
</script>

<style>
.table-transparent {
  background-color: transparent !important;
}
</style>
