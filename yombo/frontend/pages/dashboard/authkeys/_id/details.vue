<template>
  <dashboard-display-item
  :pageTitle="$t('ui.navigation.authkeys')"
  :dashboardFetchData="dashboardFetchData"
  :displayItem="displayItem"
  :apiErrors="apiErrors"
  refreshIcon
  editIcon="dashboard-authkeys-id-edit"
  deleteIcon="gateway/authkeys/delete"
  >
    <span v-if="displayItem">
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
                      {item: $t('ui.common.authkey').toLowerCase()}) }}
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
                      {item: $t('ui.common.authkey').toLowerCase()}) }}
            </div>
          </div>
        </div>
        <!-- /.col-lg-12 -->
      </div>
      <b-tabs card content-class="">
        <b-tab title="Details" active>
          <div class="row">
            <div class="col-md-6">
              <label class="detail-label-first">Label: </label><br>
              {{ displayItem.label }} <br>
              <label class="detail-label">Machine Label: </label><br>
              {{ displayItem.machine_label }} <br>
              <label class="detail-label">Description: </label><br>
              {{ displayItem.description }} <br>
              <label class="detail-label">Roles: </label><br>
                <li v-for="role_id in displayItem.roles">
                  <role-line :role_id="role_id"/>
                </li>
            </div>
            <div class="col-md-6">
              <label class="detail-label-first">Preserve key: </label><br>
              {{ displayItem.preserve_key }} <br>
              <label class="detail-label">status: </label><br>
              {{ displayItem.status }} <br>
              <label class="detail-label">Requested By: </label><br>
              {{ displayItem.request_by }} (Type:{{displayItem.request_by_type}})<br>
              <label class="detail-label">Request Context: </label><br>
              {{ displayItem.request_context }} <br>
              <label class="detail-label">last_access_at: </label><br>
              {{ displayItem.last_access_at | epoch_to_datetime_terse}} <br>
              <label class="detail-label">created_at: </label><br>
              {{ displayItem.created_at | epoch_to_datetime_terse}} <br>
              <label class="detail-label">updated_at: </label><br>
              {{ displayItem.updated_at | epoch_to_datetime_terse}} <br>
            </div>
          </div>
        </b-tab>
        <b-tab title="Debug">
          <p>AuthKey data:</p>
          <pre>{{JSON.stringify(displayItem, null, 2)}}</pre>
        </b-tab>
      </b-tabs>
    </span>
  </dashboard-display-item>
</template>

<script>
  import { dashboardApiItemMixin } from "@/mixins/dashboardApiItemMixin";
  import RoleLine from '@/components/Dashboard/SingleLines/RoleLine.vue';
  import { GW_Authkey } from '@/models/authkey'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiItemMixin],
    components: {
      RoleLine,
    },
    data() {
      return {
        metaPageTitle: this.$t('ui.navigation.authkeys'),
      };
    },
    methods: {
      dashboardFetchData(forceFetch = true) {
        let that = this;
        this.apiErrors = null;
        this.$store.dispatch('gateway/roles/refresh');
        this.$store.dispatch('gateway/authkeys/fetchOne', this.id)
          .then(function() {
            that.displayItem = GW_Authkey.query().where('id', that.id).first();
            that.$bus.$emit("listenerUpdateBreadcrumb",
              {
                index: 2,
                path: "dashboard-authkeys-id-details",
                props: {id: that.id},
                text: that.str_limit(that.displayItem["label"], 13),
              });
          })
          .catch(error => {
            console.log(JSON.stringify(error));
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      },
    },
  };
</script>

<style lang="less" scoped>
  .h4 {
    margin-top: 5px !important;
  }
</style>
