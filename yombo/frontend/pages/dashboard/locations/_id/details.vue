<template>
  <dashboard-display-item
    :pageTitle="$t('ui.common.location')"
    :dashboardFetchData="dashboardFetchData"
    :displayItem="displayItem"
    :apiErrors="apiErrors"
    refreshIcon
    editIcon="dashboard-locations-id-edit"
    deleteIcon="gateway/locations/delete"
  >
    <span v-if="displayItem">
      <label class="detail-label-first">Machine Label: </label><br>
      {{ displayItem.machine_label }} <br>
      <label class="detail-label">Label: </label><br>
      {{ displayItem.label }} <br>
      <label class="detail-label">Description: </label><br>
      {{ displayItem.description }} <br>
    </span>
  </dashboard-display-item>
</template>

<script>
  import { dashboardApiItemMixin } from "@/mixins/dashboardApiItemMixin";

  import { GW_Location } from '@/models/location';

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiItemMixin],
    methods: {
      dashboardFetchData() {
        let that = this;
        this.apiErrors = null;
        this.$bus.$emit("listenerUpdateBreadcrumb",
          {
            index: 2, path: "dashboard-locations-id-details",
            props: {id: this.id},
            text: this.$options.filters.str_limit(this.id, 10),
          });
        this.$bus.$emit("listenerDeleteBreadcrumb", 3);

        this.apiErrors = null;
        this.$store.dispatch('gateway/locations/fetchOne', this.id)
          .then(function() {
            // that.sleep(500);
            that.displayItem = GW_Location.query().where('id', that.id).first();
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
