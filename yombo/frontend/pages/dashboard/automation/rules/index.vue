<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="fa-pull-right">
            <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-devices-add')">
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
           {{ $t('ui.label.automation_rules') }}
         </h4>
           <div slot="footer" class="stats">
             <i v-on:click="refreshRequest" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
             {{$t('ui.label.updated')}} {{display_age}}
           </div>
        </div>
        <div class="card-body">
          <el-table
            :data="rules"
          >
            <el-table-column :label="$t('ui.label.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.label.description')" property="rule.config.description"></el-table-column>
            <el-table-column :label="$t('ui.common.enabled')">
              <div slot-scope="props">
                {{props.row.rule.config.enabled == true}}
              </div>
            </el-table-column>
            <el-table-column :label="$t('ui.label.created_at')" property="created_at"></el-table-column>
            <el-table-column :label="$t('ui.label.updated_at')" property="updated_at"></el-table-column>

            </el-table-column>
            <el-table-column
              align="right" :label="$t('ui.label.actions')">
              <div slot-scope="props" class="table-actions">
                <n-button @click.native="handleEdit(props.$index, props.row)"
                          class="edit"
                          type="info"
                          size="sm" round icon>
                  <i class="fa fa-edit"></i>
                </n-button>

                <template v-if="props.row.rule.config.enabled == true">
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
    rules () {
      let source = this.$store.state.gateway.automation_rules.data;
      let results = [];

      Object.keys(source).forEach(key => {
        results.push(source[key]);
      });

      return results
    },
  },

  methods: {
    handleEdit(index, row) {
      this.$router.push(this.localePath('dashboard-automation-rules-edit')+"/"+row.id);
    },
    handleDetails(index, row) {
      this.$router.push(this.localePath('dashboard-automation-rules-details')+"/"+row.id);
    },
    handleDelete(index, row) {
      this.$swal({
        title: this.$t('ui.prompt.delete_rule'),
        text: this.$t('ui.phrase.cannot_undo'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch('yombo/automation_rules/delete', row.id);
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
        title: this.$t('ui.prompt.enable_rule'),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'info',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('yombo/automation_rules/enable', row.id);
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
        title: this.$t('ui.prompt.enable_rule'),
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        type: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, disable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          let results = this.$store.dispatch('yombo/automation_rules/disable', row.id);
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
    refreshRequest() {
      this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.mesages.refreshing_data'),
          type: 'success',
          showConfirmButton: true,
          timer: 1000
      });
      this.$store.dispatch('gateway/automation_rules/fetch');
    },
    updateDisplayAge () { // called by setInterval setup in mounted()
      this.display_age =  this.$store.getters['gateway/automation_rules/display_age'](this.$i18n.locale);
    },

  },
  mounted () {
    this.updateDisplayAge();
    this.$options.interval = setInterval(this.updateDisplayAge, 1000);
    this.$store.dispatch('gateway/automation_rules/refresh');
    // this.$store.dispatch('yombo/devices/refresh');
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
};
</script>
