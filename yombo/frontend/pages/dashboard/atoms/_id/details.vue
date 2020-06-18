<template>
  <dashboard-display-item
    :pageTitle="$t('ui.common.atom')"
    :editPath="`dashboard-atoms-${id}-edit`"
    :dashboardFetchData="dashboardFetchData"
    :displayItem="displayItem"
    :apiErrors="apiErrors"
  >
    <span v-if="displayItem">
      <label class="detail-label-first">Atom Name: </label><br>
      {{ displayItem.id }} <br>
      <label class="detail-label">Value: </label><br>
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
          {{ displayItem.last_access_at | epoch_to_datetime_terse}} <br>
          <label class="detail-label">Created: </label><br>
          {{ displayItem.created_at | epoch_to_datetime_terse}} <br>
          <label class="detail-label">Updated: </label><br>
          {{ displayItem.updated_at | epoch_to_datetime_terse}} <br>
        </div>
      </div>
    </span>
  </dashboard-display-item>
</template>

<script>
  import { dashboardApiItemMixin } from "@/mixins/dashboardApiItemMixin";
  import { GW_Atom } from '@/models/atom';

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiItemMixin],
    methods: {
      dashboardFetchData(forceFetch = true) {
        let that = this;
        this.apiErrors = null;
        this.$bus.$emit("listenerUpdateBreadcrumb",
          {
            index: 2, path: "dashboard-atoms-id-details",
            props: {id: this.id},
            text: this.$options.filters.str_limit(this.id, 10),
          });
        this.$bus.$emit("listenerDeleteBreadcrumb", 3);

        this.apiErrors = null;
        this.$store.dispatch('gateway/atoms/fetchOne', this.id)
          .then(function() {
            that.displayItem = GW_Atom.query().where('id', that.id).first();
          })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      },
    },
  };
</script>
