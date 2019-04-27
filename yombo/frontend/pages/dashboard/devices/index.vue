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
          {{ this.$i18n.locale }}
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
              align="right">
              <template slot="header" slot-scope="scope">
                {{ $t('ui.label.actions')}}
              </template>
              <template slot-scope="scope">
                {{ $t('ui.label.edit')}} {{ $t('ui.label.delete')}}
              </template>
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

import humanizeDuration from 'humanize-duration';

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
      this.display_age =  this.$store.getters['devices/display_age'](this.$i18n.locale);
    }
  },
  created () {
    // this.$bus.$on('messageSent', e => console.log("DB:devices: " + e));
    this.debouncedRefresh = _.throttle(this.refresh, 5000);
    this.$store.dispatch('devices/refresh');
    this.$store.dispatch('locations/refresh');
  },
  mounted () {
    this.updateDeviceAge();
    this.$options.interval = setInterval(this.updateDeviceAge, 5000);
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
};
</script>

<style>
/*.table-transparent {*/
/*  background-color: transparent !important;*/
/*}*/
</style>
