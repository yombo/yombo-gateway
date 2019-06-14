<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
          {{ $t('ui.common.device') }}: {{item.full_label}}
          <actions path="dashboard-devices" :id="id"
                   edit
                   enabledispatch="yombo/devices/enable"
                   disabledispatch="yombo/devices/disable"
                   deletedispatch="yombo/devices/delete"
          ></actions>
        </h4>
        </div>
<!--          {{ $t('ui.common.device')}}: {{id}}-->
<!--          <p>{{item}}</p>-->
        <template v-if="item.status == 0">
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
        <template v-if="item.status == 2">
            <div class="row">
                <div class="col-lg-12">
                    <div class="panel panel-default panel-red">
                        <div class="panel-heading">
                            <label>Device Deleted</label>
                        </div>
                        <!-- /.panel-heading -->
                        <div class="panel-body">
                            <label style="margin-top: 0px; margin-bottom: 0px">This device has been deleted and is not accessible to the
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
              <div class="col-md-6">
                  <!-- /.panel-heading -->
                      <label class="detail-label-first">Gateway: </label><br>
                      {{ gateway.label }} <br>
<!--                            {{ 32.5 | temperature}}-->
                      <label class="detail-label">Label: </label><br>
                      {{ item.label }} <br>
                      <i>Effective:</i> {{ location(item.area_id).label }} {{item.label}}<br>
                      <label class="detail-label">Machine Label: </label><br>
                      {{ item.machine_label }}<br>
                      <label class="detail-label">Location: </label><br>
                      {{ location(item.location_id).label }} -> {{ location(item.area_id).label }}<br>
                      <label class="detail-label">Description: </label><br>
                      {{ item.description }}<br>
                      <label class="detail-label">Status:</label><br>
                      {{ item.status }}<br>
                      <label class="detail-label">Pin Required // Pin Code: </label><br>
                      {{ item.pin_required|yes_no }} // {{ item.pin_code }} <br>
                      <label class="detail-label">Device Type: </label><br>
                      {{ item.device_type_id }}<br>

                <!-- /.panel-body -->
              </div>
              <div class="col-md-6">
                  <!-- /.panel-heading -->
                      <label class="detail-label">Controllable: </label><br>
                      {{ item.is_controllable|yes_no }}<br>
                      <label class="detail-label">Allow Direct Control: </label><br>
                      {{ item.is_direct_controllable|yes_no }}<br>
                      <label class="detail-label">Allowed in scenes: </label><br>
                      {{ item.is_allowed_in_scenes|yes_no }}<br>
                      <label class="detail-label">Statistic Type: </label><br>
                      {{ item.statistic_type }}<br>
                      <label class="detail-label">Statistic Label: </label><br>
                      {{ item.statistic_label_slug }}<br>
                      <label class="detail-label">Statistic Bucket Size: </label><br>
                      {{ item.statistic_bucket_size }}<br>
                      <label class="detail-label">Statistic Lifetime: </label><br>
                      {{ item.statistic_lifetime }}<br>
                      <label class="detail-label">Updated At: </label><br>
                      {{ item.updated_at }}<br>
                      <label class="detail-label">Created At: </label><br>
                      {{ item.created_at }}<br>
                <!-- /.panel-body -->
              </div>
            </div>
          </b-tab>
          <b-tab title="History">
            <p>I'm the history tab. Device state change history should be displayed here.</p>
          </b-tab>
          <b-tab title="Permissions">
            <p>List permissions of users that can view/edit/control this device.</p>
          </b-tab>
          <b-tab title="Variables">
            <p>Show/edit variables for this device.</p>
          </b-tab>
          <b-tab title="Debug">
            <p>Debug details about this device.</p>
          </b-tab>
        </b-tabs>
      </card>
    </div>
  </div>
</template>

<script>
import { Actions } from '@/components/Dashboard/Actions';
// import { ActionDelete, ActionDetails, ActionDisable, ActionEdit, ActionEnable } from '@/components/Dashboard/Actions';

import { Table, TableColumn } from 'element-ui';

import Device from '@/models/device'
import Gateway from '@/models/gateway'
import Location from '@/models/location'

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
      gateway: {},
    };
  },
  computed: {
    item () {
      return Device.query().where('id', this.id).first()
    },
  },
  methods: {
    location: function(id) {
      return Location.query().where('id', id).first();
    }
  },
  mounted () {
    this.$bus.$emit("listenerUpdateBreadcrumb",
      {index: 2, path: "dashboard-devices-id-details", props: {id: this.id}, text: this.item.label});
    this.$bus.$emit("listenerDeleteBreadcrumb", 3);
    this.$store.dispatch('yombo/devices/refresh');
    this.$store.dispatch('yombo/locations/refresh');
    this.gateway = Gateway.query().where('id', this.item.gateway_id).first()
  },
};
</script>

<style lang="less" scoped>
  .h4 {
    margin-top: 5px !important;
  }
  .detail-label {
    color: black !important;
    font-size: 16px;
    font-weight: 600;
    margin-top: 15px;
    margin-bottom: 0px
  }
  .detail-label-first {
    .detail-label;
    margin-top: 0px;
  }
</style>
