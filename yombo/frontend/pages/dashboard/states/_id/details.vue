<template>
  <dashboard-display-item
    :pageTitle="$t('ui.navigation.states')"
    :typeLabel="$t('ui.common.state')"
    :displayItem="displayItem"
    :id="id"
    :itemLabel="id"
    :apiErrors="apiErrors"
    :dashboardFetchData="dashboardFetchData"
    refreshIcon
    editIcon="dashboard-states-id-edit"
    deleteIcon="gateway/states/delete"
  >
    <span v-if="displayItem">
      <label class="detail-label-first">Value: </label><br>
      {{ displayItem.value }} <br>
      <label class="detail-label">Value Human: </label><br>
      {{ displayItem.value_human }} <br>
      <div class="row">
        <div class="col-md-6">
          <label class="detail-label">Value Type: </label><br>
          {{ displayItem.value_type }} <br>
          <label class="detail-label">Request By: </label><br>
          {{ displayItem.request_by }} <br>
          <label class="detail-label">Request By Type: </label><br>
          {{ displayItem.request_by_type }} <br>
          <label class="detail-label">Request Context: </label><br>
          {{ displayItem.request_context }} <br>
        </div>
        <div class="col-md-6">
          <label class="detail-label">Last Access: </label><br>
          {{ displayItem.last_access_at }} <br>
          <label class="detail-label">Created: </label><br>
          {{ displayItem.created_at }} <br>
          <label class="detail-label">Updated: </label><br>
          {{ displayItem.updated_at }} <br>
        </div>
      </div>
    </span>
  </dashboard-display-item>
</template>

<script>
  import { GW_State } from '@/models/state';
  import { dashboardApiItemMixin } from "@/mixins/dashboardApiItemMixin";

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiItemMixin],
    methods: {
      dashboardFetchData() {
        let that = this;
        this.apiErrors = null;
        this.$bus.$emit("listenerUpdateBreadcrumb",
          {
            index: 2, path: "dashboard-states-id-details",
            props: {id: this.id},
            text: this.$options.filters.str_limit(this.id, 10),
          });
        this.$bus.$emit("listenerDeleteBreadcrumb", 3);

        this.apiErrors = null;
        this.$store.dispatch('gateway/states/fetchOne', this.id)
          .then(function() {
            // that.sleep(500);
            that.displayItem = GW_State.query().where('id', that.id).first();
          })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      },
      // sleep(milliseconds) {
      //   const date = Date.now();
      //   let currentDate = null;
      //   do {
      //     currentDate = Date.now();
      //   } while (currentDate - date < milliseconds);
      // }
    },
  };
</script>
