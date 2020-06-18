<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.roles')"
    addPath="dashboard-roles-add"
    displayAgePath="gateway/roles/display_age"
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
            detailIcon="dashboard-roles-id-details"
            editIcon="dashboard-roles-id-edit"
            deleteIcon="gateway/roles/delete"
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

  import { GW_Role } from '@/models/role'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "roles",
        tableColumns1: [
          {key: 'label', label: this.$i18n.t('ui.common.label') },
          {key: 'machine_label', label: this.$i18n.t('ui.common.machine_label') },
          {key: 'description',  label: this.$i18n.t('ui.common.description') },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ],
      };
    },
    methods: {
      dashboardGetFuseData() {
        console.log('dashboardGetFuseData roles');
        this.dashboardDisplayItems = GW_Role.query()
                                   .orderBy('label', 'asc')
                                   .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.5 },
            { name: 'machine_label', weight: 0.5 },
          ]
        });
      }
    },
  };
</script>
