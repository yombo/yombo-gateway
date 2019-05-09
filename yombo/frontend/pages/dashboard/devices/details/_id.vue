<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.navigations.devices') }}
         </h4>
        </div>
        <div class="card-body">
          {{ $t('ui.label.device')}}: {{id}}
        </div>
        <p>{{item}}</p>
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
      id: this.$route.params.id,
    };
  },
  computed: {
    item () {
      return this.$store.state.gateway.device_commands.data[this.id];
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
  },
  mounted () {
    // console.log("devices mounted....");
  },
  beforeDestroy () {
    // console.log("device before destroy")
  },
};
</script>

<style>
/*.table-transparent {*/
/*  background-color: transparent !important;*/
/*}*/
</style>
