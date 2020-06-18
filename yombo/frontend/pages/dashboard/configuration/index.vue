<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.configuration')"
    addPath="dashboard-configuration-add"
    displayAgePath="gateway/configs/display_age"
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
        <template v-slot:cell(value)="data">
          {{ data.item.value | str_limit(18) }}
        </template>
        <template v-slot:cell(fetches)="data">
          {{ data.item.fetches }} / {{ data.item.writes }}
        </template>
        <template v-slot:cell(actions)="data">
          <dashboard-row-actions
            :typeLabel="$t('ui.common.location')"
            :displayItem="data.item"
            :itemLabel="data.item.id"
            :id="data.item.id"
            detailIcon="dashboard-configs-id-details"
            editIcon="dashboard-configs-id-edit"
            deleteIcon="gateway/configs/delete"
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

  import { GW_Config } from '@/models/config'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "configs",
        tableColumns1: [
          {key: 'id', label: this.$i18n.t('ui.common.configs') },
          {key: 'value', label: this.$i18n.t('ui.common.machine_label') },
          {key: 'fetches',  label: `${this.$i18n.t('ui.common.reads')} / ${this.$i18n.t('ui.common.writes')}` },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ],
      }
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Config.query()
                                     .orderBy('config', 'asc')
                                     .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'id', weight: 0.5 },
            { name: 'value', weight: 0.25 },
            { name: 'value_human', weight: 0.25 },
          ]
        });
      }
    },
  };
</script>
