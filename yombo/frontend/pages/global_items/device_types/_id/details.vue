<template>
  <dashboard-display-item
    :pageTitle="$t('ui.navigation.device_types')"
    :dashboardFetchData="dashboardFetchData"
    :displayItem="displayItem"
    :apiErrors="apiErrors"
    refreshIcon
    editIcon="global_items-device_types-id-edit"
    deleteIcon="gateway/device_types/delete"
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
                    <i>Effective:</i> {{ location(displayItem.area_id)["label"] }} {{displayItem.label}}<br>
                    <label class="detail-label">Machine Label: </label><br>
                    {{ displayItem.machine_label }}<br>
                    <label class="detail-label">Location: </label><br>
                    {{ location(displayItem.location_id)["label"] }} -> {{ location(displayItem.area_id)["label"] }}<br>
                    <label class="detail-label">Description: </label><br>
                    {{ displayItem.description }}<br>
                    <label class="detail-label">Status:</label><br>
                    {{ displayItem.status }}<br>
                    <label class="detail-label">Pin Required // Pin Code: </label><br>
                    {{ displayItem.pin_required|yes_no }} // {{ displayItem.pin_code }} <br>
                    <label class="detail-label">Device Type: </label><br>
                    {{ getDeviceType(displayItem.device_type_id)["label"] }}<br>

              <!-- /.panel-body -->
            </div>
            <div class="col-md-6">
                <!-- /.panel-heading -->
                    <label class="detail-label-first">Scene Controllable: </label><br>
                    {{ displayItem.is_scene_controllable|yes_no }}<br>
                    <label class="detail-label">Allow Direct Control: </label><br>
                    {{ displayItem.is_direct_controllable|yes_no }}<br>
                    <label class="detail-label">Allowed in scenes: </label><br>
                    {{ displayItem.is_allowed_in_scenes|yes_no }}<br>
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

  import { GW_Location } from '@/models/location'

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
        this.$store.dispatch('gateway/device_types/fetchOne', this.id)
          .then(function() {
            // that.sleep(500);
            that.displayItem = GW_Location.query().where('id', that.id).first();
          })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      }
    },
    // beforeMount: function beforeMount() {
    //   this.gateway_id = this.$store.state.gateway.systeminfo.gateway_id;
    //   console.log("local before mount..2");
    //   this.$store.dispatch('gateway/locations/refresh');
    //   console.log("local before mount..3");
    // },
  };
</script>

<style lang="less" scoped>
  .h4 {
    margin-top: 5px !important;
  }
</style>
