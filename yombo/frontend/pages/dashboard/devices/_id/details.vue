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
        <div class="card-body">
          {{ $t('ui.common.device')}}: {{id}}
          <p>{{item}}</p>

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
          <div class="row">
            <div class="col-lg-12">
              <b-tabs card content-class="">
                <b-tab title="Details" active>
                  <div class="col-lg-6 col-md-6">
                      <!-- /.panel-heading -->
                          <label class="detail-label-first">Gateway: </label><br>
                          {{ gateway.label }} <br>
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
                    <!-- /.panel-body -->
                  </div>
                </b-tab>
                <b-tab title="History">
                  <p>I'm the second tab</p>
                </b-tab>
                <b-tab title="Permissions">
                  <p>I'm a disabled tab!</p>
                </b-tab>
                <b-tab title="Variables">
                  <p>I'm a disabled tab!</p>
                </b-tab>
                <b-tab title="Debug">
                  <p>I'm a disabled tab!</p>
                </b-tab>
              </b-tabs>
            </div>
          </div>
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { Actions } from '@/components/Dashboard/Actions';
import { ActionDelete, ActionDetails, ActionDisable, ActionEdit, ActionEnable } from '@/components/Dashboard/Actions';

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
    ActionEdit,
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
      console.log("location id: " + id);
      console.log(Location.query().where('id', id).first());
      return Location.query().where('id', id).first();
    }
  },
  mounted () {
    this.$store.dispatch('yombo/devices/refresh');
    this.$store.dispatch('yombo/locations/fetch');

    this.gateway = Gateway.query().where('id', this.item.gateway_id).first()
  },
  beforeDestroy () {
    // console.log("device before destroy")
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
