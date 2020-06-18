<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.locations')"
    addPath="dashboard-locations-add"
    displayAgePath="gateway/locations/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <dashboard-table-pagination
          tableIndex="1"
          tableName="indexTable1"
          position="top"
          :rowCount="dashboardQueriedData.length"
        >
      </dashboard-table-pagination>
      <b-table striped hover
               id="indexTable1"
               :items="dashboardQueriedData"
               :per-page="dashboardTableRowsPerPage"
               :current-page="dashboardTablePage1"
               :fields="tableColumns1"
               small
               >
        <template v-slot:cell(actions)="data">
          <dashboard-row-actions
            :typeLabel="$t('ui.common.roles')"
            :displayItem="data.item"
            :itemLabel="data.item.id"
            :id="data.item.id"
            detailIcon="dashboard-locations-id-details"
            editIcon="dashboard-locations-id-edit"
            deleteIcon="gateway/locations/delete"
          ></dashboard-row-actions>
        </template>
      </b-table>
      <dashboard-table-pagination
          tableIndex="1"
          tableName="indexTable1"
          position="bottom"
          :rowCount="dashboardQueriedData.length"
        >
      </dashboard-table-pagination>
    </span>
  </dashboard-display-index>
</template>

<script>
  import Fuse from 'fuse.js';

  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";

  import { GW_Location } from '@/models/location'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "locations",
        tableColumns1: [
          {key: 'id', label: this.$i18n.t('ui.common.atom') },
          {key: 'machine_label', label: this.$i18n.t('ui.common.machine_label') },
          {key: 'description',  label: this.$i18n.t('ui.common.description') },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ]
      }
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Location.query()
                                       .where('location_type', 'location')
                                       .orderBy('label', 'asc')
                                       .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.5 },
            { name: 'machine_label', weight: 0.3 },
            { name: 'description', weight: 0.2 },
          ]
        });
      }
    },
  };
</script>
