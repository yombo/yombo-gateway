<template>
  <div class="row" v-if="module">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
          {{ $t('ui.common.gateway_module') }}: {{module.label}}<br>
<!--          <actions path="dashboard-devices" :id="id"-->
<!--                   edit-->
<!--                   enabledispatch="yombo/devices/enable"-->
<!--                   disabledispatch="yombo/devices/disable"-->
<!--                   deletedispatch="yombo/devices/delete"-->
<!--          ></actions>-->
        </h4>
        </div>
        <template v-if="module.status == 0">
          <div class="row">
              <div class="col-lg-12">
                  <div class="panel panel-default panel-red">
                      <div class="panel-heading">
                          <label>Device Disabled</label>
                      </div>
                      <!-- /.panel-heading -->
                      <div class="panel-body">
                          <label style="margin-top: 0px; margin-bottom: 0px">This device has been disabled and is not accessible to the
                          system for automation purposes.</label>
                      </div>
                  </div>
              </div>
              <!-- /.col-lg-12 -->
          </div>
        </template>
        <template v-if="module.status == 2">
            <div class="row">
                <div class="col-lg-12">
                    <div class="panel panel-default panel-red">
                        <div class="panel-heading">
                            <label>Module Deleted</label>
                        </div>
                        <!-- /.panel-heading -->
                        <div class="panel-body">
                            <label style="margin-top: 0px; margin-bottom: 0px">This module has been deleted and is not accessible to the
                            system for automation purposes.</label>
                        </div>
                    </div>
                </div>
                <!-- /.col-lg-12 -->
            </div>
        </template>
        <b-tabs card content-class="">
          <b-tab title="Details" active>
            <div class="row">
              <div class="col-md-8">
                <label class="detail-label">Description: </label><br>
                <div class="framed-content">
                  <span v-html="module.description_html"></span>
                </div>
              </div>
              <div class="col-md-4">
                <label class="detail-label-first">Label: </label><br>
                {{ module.label }} <br>
                <label class="detail-label">Machine Label: </label><br>
                {{ module.machine_label }}<br>
                <label class="detail-label">Module Type: </label><br>
                {{ module.module_type }}<br>
                <span v-if="module.respository_link">
                  <label class="detail-label">Repository Link: </label><br>
                  <a :href="module.respository_link">View Source</a><br>
                </span>
                <span v-if="module.issue_tracker_link">
                  <label class="detail-label">Issue Tracker Link: </label><br>
                  <a :href="module.issue_tracker_link">View Source</a><br>
                </span>
                <span v-if="module.doc_link">
                  <label class="detail-label">Documentation Link: </label><br>
                  <a :href="module.doc_link">View Source</a><br>
                </span>
                <label class="detail-label">Install Count: </label><br>
                {{ module.install_count }}<br>
                <label class="detail-label">Public: </label><br>
                {{ module.public }}<br>
                <label class="detail-label">Status: </label><br>
                {{ module.status }}<br>
                <label class="detail-label">Updated At: </label><br>
                {{ module.updated_at }}<br>
                <label class="detail-label">Created At: </label><br>
                {{ module.created_at }}<br>
              </div>
            </div>
          </b-tab>
          <b-tab title="Variables">
            <div class="framed-content variables" v-for="variable_group in variable_groups">
              <h3 class="card-title">{{variable_group.group_label}}</h3>
              <h6 class="description">{{variable_group.group_description}}</h6>
              <div class="variable-data" v-for="variable_field in variable_fields(variable_group.id)">
                <el-table :data="variable_data(variable_field.id)">
                  <el-table-column :label="variable_field.field_label" property="data"></el-table-column>
                  <el-table-column :label="$t('ui.common.weight')" property="data_weight"></el-table-column>
                </el-table>
              </div>
            </div>
            <p>Show/edit variables for this module.</p>
          </b-tab>
          <b-tab title="Debug">
            <pre>{{ JSON.stringify(module, null, 2) }}</pre>
          </b-tab>
        </b-tabs>
      </card>
    </div>
  </div>
</template>

<script>
import { Actions } from '@/components/Dashboard/Actions';
import { Table, TableColumn } from 'element-ui';

import { GW_Module } from '@/models/module'
import { GW_Gateway } from '@/models/gateway'
import { GW_Variable_Data } from '@/models/variable_data'
import { GW_Variable_Field } from '@/models/variable_fields';
import { GW_Variable_Group } from '@/models/variable_groups';

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    Actions,
  },
  data() {
    return {
      id: this.$route.params.id,
      module: null,
      gateway: null,
      variable_groups: null,
      gateway_id: null,
    };
  },
  methods: {
    variable_data: function (variable_field_id) {
      return GW_Variable_Data.query()
                          .where('variable_field_id', variable_field_id)
                          .where('variable_relation_id', this.id)
                          .where('variable_relation_type', 'module')
                          .orderBy('data_weight', 'asc')
                          .get();
    },
    variable_fields: function (variable_group_id) {
      return GW_Variable_Field.query()
                           .where('variable_group_id', variable_group_id)
                           .orderBy('field_weight', 'asc')
                           .get();
    },
  },
  beforeMount() {
    this.gateway = this.$store.state.gateway.systeminfo.gateway_id;
    let that = this;
    this.$store.dispatch('gateway/gateway_modules/fetch')
      .then(function() {
        that.module = GW_Module.query().where('id', that.id).first();
        that.$bus.$emit("listenerUpdateBreadcrumb",
          {index: 2, path: "dashboard-gateway_modules-id-details", props: {id: that.id}, text: that.module.label});
        that.$bus.$emit("listenerDeleteBreadcrumb", 3);
        that.$bus.$emit("listenerAppendBreadcrumb",
          {index: 2, path: "dashboard-gateway_modules-id-details", props: {id: that.id}, text: "ui.navigation.details"});
      });
    this.$store.dispatch('gateway/variable_groups/fetch')
      .then(function() {
        that.variable_groups = GW_Variable_Group.query()
                                 .where('group_relation_type', 'module')
                                 .where('group_relation_id', that.id)
                                 .orderBy('group_weight', 'asc')
                                 .get();
      });
    this.$store.dispatch('gateway/variable_fields/fetch');
    this.$store.dispatch('gateway/variable_data/fetch');
    this.$store.dispatch('gateway/gateways/refresh')
      .then(function() {
      that.gateway = GW_Gateway.query().where('id', that.id).first();
      });
    console.log(`gateway_id: ${this.$store.state.gateway.systeminfo}`);
  },
};
</script>

<style lang="less" scoped>
  .h4 {
    margin-top: 5px !important;
  }
</style>
