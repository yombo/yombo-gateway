<template>
  <dashboard-display-item
    :pageTitle="$t('ui.common.device')"
    :dashboardFetchData="dashboardFetchData"
    :displayItem="displayItem"
    :apiErrors="apiErrors"
    refreshIcon
    editIcon="dashboard-devices-id-edit"
    deleteIcon="gateway/devices/delete"
  >
    <span v-if="displayItem && gateway">
      <div class="row" v-if="displayItem.status == 0">
        <div class="col-lg-12">
          <div class="panel panel-default panel-red">
            <div class="panel-heading">
              <label>Device Disabled</label>
            </div>
            <!-- /.panel-heading -->
            <div class="panel-body">
              <label style="margin-top: 0px; margin-bottom: 0px">
                {{ $t('ui.phrase.deleted_item_cant_be_used',
                      {item: $t('ui.common.device').toLowerCase()}) }}
              </label>
            </div>
          </div>
        </div>
      </div>
      <div class="row" v-if="displayItem.status == 2">
        <div class="col-lg-12">
          <div class="panel panel-default panel-red">
            <div class="panel-heading">
              <label>Device Deleted</label>
            </div>
            <!-- /.panel-heading -->
            <div class="panel-body">
                {{ $t('ui.phrase.deleted_item_cant_be_used',
                      {item: $t('ui.common.device').toLowerCase()}) }}
            </div>
          </div>
        </div>
        <!-- /.col-lg-12 -->
      </div>
      <b-tabs card content-class="item-tabs">
        <b-tab title="Details" active  class="framed-content">
          <div class="row">
            <div class="col-md-6">
                <!-- /.panel-heading -->
                    <label class="detail-label-first">Gateway: </label><br>
                    {{ gateway.label }} <br>
<!--                            {{  39 | temperature}}-->
                    <label class="detail-label">Label: </label><br>
                    {{ displayItem.label }} <br>
                    <i>Effective:</i> {{ getLocation(displayItem.area_id).label }} {{displayItem.label}}<br>
                    <label class="detail-label">Machine Label: </label><br>
                    {{ displayItem.machine_label }}<br>
                    <label class="detail-label">Location: </label><br>
                    {{ getLocation(displayItem.location_id).label }} -> {{ getLocation(displayItem.area_id).label }}<br>
                    <label class="detail-label">Description: </label><br>
                    {{ displayItem.description }}<br>
                    <label class="detail-label">Status:</label><br>
                    {{ displayItem.status }}<br>
                    <label class="detail-label">Pin Required // Pin Code: </label><br>
                    {{ displayItem.pin_required|yes_no }} // {{ displayItem.pin_code }} <br>
                    <label class="detail-label">Device Type: </label><br>

                    <nuxt-link :to="localePath(
                      {name: 'global_items-device_types-id-details', params: {id: getDeviceType(displayItem.device_type_id)['id']} }
                      )">{{ getDeviceType(displayItem.device_type_id).label }}
                    </nuxt-link>
                    <br>

              <!-- /.panel-body -->
            </div>
            <div class="col-md-6">
                <!-- /.panel-heading -->
                    <label class="detail-label-first">Scene Controllable: </label><br>
                    {{ displayItem.scene_controllable|yes_no }}<br>
                    <label class="detail-label">Allowed in scenes: </label><br>
                    {{ displayItem.is_allowed_in_scenes|yes_no }}<br>
                    <label class="detail-label">Allow Direct Control: </label><br>
                    {{ displayItem.is_direct_controllable|yes_no }}<br>
                    <label class="detail-label">Statistic Type: </label><br>
                    {{ displayItem.statistic_type }}<br>
                    <label class="detail-label">Statistic Label: </label><br>
                    {{ displayItem.statistic_label_slug }}<br>
                    <label class="detail-label">Statistic Bucket Size: </label><br>
                    {{ displayItem.statistic_bucket_size }}<br>
                    <label class="detail-label">Statistic Lifetime: </label><br>
                    {{ displayItem.statistic_lifetime }}<br>
                    <label class="detail-label">Updated At: </label><br>
                    {{ displayItem.updated_at }}<br>
                    <label class="detail-label">Created At: </label><br>
                    {{ displayItem.created_at }}<br>
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
          <p>Device data:</p>
          <pre>{{JSON.stringify(displayItem, null, 2)}}</pre>
        </b-tab>
      </b-tabs>
    </span>
  </dashboard-display-item>
</template>

<script>
  import { dashboardApiItemMixin } from "@/mixins/dashboardApiItemMixin";

  import { GW_Device } from '@/models/device'
  import { GW_Gateway } from '@/models/gateway'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiItemMixin],
    data() {
      return {
        gateway: null,
      };
    },
    methods: {
      dashboardFetchData() {
        let that = this;
        this.apiErrors = null;
        this.$store.dispatch('gateway/devices/fetchOne', this.id)
          .then(function() {
            that.displayItem = GW_Device.query().where('id', that.id).first();
            that.$bus.$emit("listenerUpdateBreadcrumb",
              {
                index: 2,
                path: "dashboard-devices-id-details",
                props: {id: that.id},
                text: this.$options.filters.str_limit(that.displayItem["label"], 12),

              });
            that.$bus.$emit("listenerDeleteBreadcrumb", 3);
            that.$store.dispatch('gateway/gateways/refresh')
              .then(function() {
                that.gateway = GW_Gateway.query().where('id', that.displayItem.gateway_id).first();
              })
              .catch(error => {
                that.apiErrors = this.$handleApiErrorResponse(error);
              })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
        });
      }
    },
    beforeMount: function beforeMount() {
      console.log("local before mount..");
      this.gateway_id = this.$store.state.gateway.systeminfo.gateway_id;
      console.log("local before mount..2");
      this.$store.dispatch('gateway/locations/refresh');
      console.log("local before mount..3");
    },
  };
</script>

<style lang="less" scoped>
  .h4 {
    margin-top: 5px !important;
  }
</style>
