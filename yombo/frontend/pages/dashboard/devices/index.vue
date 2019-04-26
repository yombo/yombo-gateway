<template>
  <div class="row">
    <div class="col-md-12">
      <p>
      <span v-on:click="refreshRequest" title="Reload devices" style="cursor:pointer;">
        <i v-on:click="refreshRequest" class="fas fa-sync-alt fa-pull-left" style="font-size: 1em; color: darkgreen;"></i>
      </span>

      <a href="#/devices/add" title="New Device" class="btn btn-primary fa-pull-right" role="button">
          <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
      </p>
      <br>
      <ul>
        <li v-for="device in devices">
         {{ device.label }}
        </li>
      </ul>
    </div>

    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <h4 class="card-title">Striped table</h4>
        </div>
        <el-table :data="tableData">
          <el-table-column min-width="150" label="Name" property="name"></el-table-column>
          <el-table-column min-width="150" label="Country" property="country"></el-table-column>
          <el-table-column min-width="150" label="City" property="city"></el-table-column>
          <el-table-column min-width="150" align="right" header-align="right" label="Salary" property="salary"></el-table-column>
        </el-table>
      </card>
    </div>

    <div class="col-md-12">
      <card class="card-plain" card-body-classes="table-full-width">
        <div slot="header">
          <h4 class="card-title">Table on Plain Background</h4>
        </div>
        <el-table header-cell-class-name="table-transparent"
                  header-row-class-name="table-transparent"
                  row-class-name="table-transparent"
                  :data="tableData">
          <el-table-column min-width="150" label="Name" property="name"></el-table-column>
          <el-table-column min-width="150" label="Country" property="country"></el-table-column>
          <el-table-column min-width="150" label="City" property="city"></el-table-column>
          <el-table-column min-width="150" align="right" header-align="right" label="Salary" property="salary"></el-table-column>
        </el-table>
      </card>
    </div>

    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <h4 class="card-title">Regular Table with Colors</h4>
        </div>
        <el-table :row-class-name="tableRowClassName"
                  :data="tableData">
          <el-table-column min-width="150" label="Name" property="name"></el-table-column>
          <el-table-column min-width="150" label="Country" property="country"></el-table-column>
          <el-table-column min-width="150" label="City" property="city"></el-table-column>
          <el-table-column min-width="150" align="right" header-align="right" label="Salary" property="salary"></el-table-column>
        </el-table>
      </card>
    </div>

  </div>
</template>
<script>
import { Table, TableColumn } from 'element-ui';
import _ from 'lodash';

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn
  },
  data() {
    return {
      tableData: [
        {
          id: 1,
          name: 'Dakota Rice',
          salary: '$36.738',
          country: 'Niger',
          city: 'Oud-Turnhout'
        },
        {
          id: 2,
          name: 'Minerva Hooper',
          salary: '$23,789',
          country: 'Curaçao',
          city: 'Sinaai-Waas'
        },
        {
          id: 3,
          name: 'Sage Rodriguez',
          salary: '$56,142',
          country: 'Netherlands',
          city: 'Baileux'
        },
        {
          id: 4,
          name: 'Philip Chaney',
          salary: '$38,735',
          country: 'Korea, South',
          city: 'Overland Park'
        },
        {
          id: 5,
          name: 'Doris Greene',
          salary: '$63,542',
          country: 'Malawi',
          city: 'Feldkirchen in Kärnten'
        }
      ]
    };
  },
  computed: {
    devices () {
      return this.$store.state.devices.devices
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
      // this.$swal('Heading', 'this is a Heading', 'OK');

      this.$swal({
          title: __('On it!'),
          text: __('Refreshing data'),
          type: 'success',
          showConfirmButton: true,
          timer: 1000
      });
    },
    refresh() {
      this.$store.dispatch('devices/fetch');
    }
  },
  created () {
    // console.log("device Index created.." + Object.keys(this.devices));
    // console.log("devices last updated:" + this.last_download_at);
    console.log(this.last_download_at);
    console.log(Math.floor(Date.now()/1000) - 15);
    if (this.last_download_at <= Math.floor(Date.now()/1000) - 15) {
      console.log("It's too old....");
      this.$store.dispatch('devices/fetch');
    }
    this.debouncedRefresh = _.throttle(this.refresh, 5000);
    // let tempdata = this.$store.getters['jv/get']({'_jv': {'type': 'gateways'}});
    // if (Object.keys(tempdata).length == 0) {
    //     this.$store.dispatch('jv/get', 'gateways')
    // }
    //     this.$store.dispatch('devices/fetchDevices');
    // if (this.devices.length == 0) {
    //     this.$store.dispatch('devices/fetch');
    // }
    // console.log("tempdate: ");
    // console.log(this.$store.getters['jv/get']({'_jv': {'type': 'system/info'}}));
//
//     this.$store.dispatch('jv/get', this.apisource)
//         .then(data => {
//             console.log(data);
//         });
  }


};
</script>
<style>
.table-transparent {
  background-color: transparent !important;
}
</style>
