<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.atoms')"
    displayAgePath="gateway/atoms/display_age"
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
        <template v-slot:cell(updated_at)="data">
          {{ data.value | epoch_to_datetime_terse }}
        </template>
        <template v-slot:cell(actions)="data">
          <dashboard-row-actions
            :typeLabel="$t('ui.common.atom')"
            :displayItem="data.item"
            :itemLabel="data.item.id"
            :id="data.item.id"
            detailIcon="dashboard-atoms-id-details"
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
  import { GW_Atom } from '@/models/atom'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "atoms",
        tableColumns1: [
          {key: 'id', label: this.$i18n.t('ui.common.atom') },
          {key: 'value_human', label: this.$i18n.t('ui.common.value') },
          {key: 'updated_at',  label: this.$i18n.t('ui.common.updated_at') },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ]
      };
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Atom.query()
                                            .orderBy('id', 'asc')
                                            .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'id', weight: 0.5 },
            { name: 'value_human', weight: 0.3 },
            { name: 'value', weight: 0.2 },
          ]
        });
      }
    },
  };
</script>
