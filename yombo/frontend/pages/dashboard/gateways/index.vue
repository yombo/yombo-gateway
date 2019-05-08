<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="fa-pull-right">
            <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-gateways-add')">
              <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">
                <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
                </button>
            </nuxt-link>
          <br>
           <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.label.search_ddd')"/>
          </div>
        <h4 class="card-title">
           {{ $t('ui.navigation.gateways') }}
         </h4>
           <div slot="footer" class="stats">
             <i v-on:click="refreshRequest" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
             {{$t('ui.label.updated')}} {{display_age}}
           </div>
        </div>
        <div class="card-body">
          <el-table
            :data="items.filter(data => !search
             || data.label.toLowerCase().includes(search.toLowerCase())
             || data.description.toLowerCase().includes(search.toLowerCase())
             )"
          >
            <el-table-column :label="$t('ui.label.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.label.description')" property="description"></el-table-column>
            <el-table-column :label="$t('ui.navigation.status')" property="status"></el-table-column>
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

import Gateway from '@/models/gateway'

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
    items () {
      return Gateway.query().orderBy('label', 'desc').get()
    },
  },

  methods: {
    handleEdit(index, row) {
      this.$router.push(this.localePath('dashboard-gateways-edit')+"/"+row.id);
    },
    handleDelete(index, row) {
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
    async handleEnable(index, row) {
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
    async handleDisable(index, row) {
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
    async refreshRequest() {
      this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.mesages.refreshing_data'),
          type: 'success',
          showConfirmButton: true,
          timer: 1000
      });
      await this.$store.dispatch('yombo/gateways/fetch');
    },
    updateDataAge () { // called by setInterval setup in mounted()
      this.display_age =  this.$store.getters['yombo/gateways/display_age'](this.$i18n.locale);
    },

  },
  async mounted () {
    this.updateDataAge();
    this.$options.interval = setInterval(this.updateDataAge, 1000);
    await this.$store.dispatch('yombo/gateways/refresh');
    await this.$store.dispatch('yombo/locations/refresh');
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
};
</script>
