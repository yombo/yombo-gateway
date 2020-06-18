<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.devices')"
    addPath="dashboard-devices-add_device"
    displayAgePath="gateway/devices/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <b-tabs nav-class="nav-tabs-primary" v-model="tabAnchorIndex">
        <b-tab title="This GW" href="#local" @click="tabAnchorChange('local')">
          <dashboard-table-pagination
              tableIndex="1"
              tableName="indexTable1"
              position="top"
              :rowCount="dataCluster.length"
            >
          </dashboard-table-pagination>
          <b-table striped hover
              id="indexTable1"
              :items="dataLocal"
              :per-page="dashboardTableRowsPerPage"
              :current-page="dashboardTablePage1"
              :fields="tableColumns1"
              small
            >
            <template v-slot:cell(actions)="data">
              <dashboard-row-actions
                :typeLabel="$t('ui.common.location')"
                :displayItem="data.item"
                :itemLabel="data.item.id"
                :id="data.item.id"
                detailIcon="dashboard-devices-id-details"
                editIcon="dashboard-devices-id-edit"
                deleteIcon="gateway/devices/delete"
                disableIcon="gateway/devices/enable"
                enableIcon="gateway/devices/disable"
              ></dashboard-row-actions>
            </template>
          </b-table>
          <dashboard-table-pagination
              tableIndex="1"
              tableName="indexTable1"
              position="bottom"
              :rowCount="dataCluster.length"
            >
          </dashboard-table-pagination>
        </b-tab>

        <b-tab title="Cluster" href="#cluster" @click="tabAnchorChange('cluster')">
          <dashboard-table-pagination
              tableIndex="2"
              tableName="indexTable2"
              position="top"
              :rowCount="dataCluster.length"
            >
          </dashboard-table-pagination>
          <b-table striped hover
              id="indexTable2"
              :items="dataCluster"
              :per-page="dashboardTableRowsPerPage"
              :current-page="dashboardTablePage2"
              :fields="tableColumns2"
              small
            >
            <template v-slot:cell(gateway_id)="data">
              {{ getGateway(data.value).label }}
            </template>
            <template v-slot:cell(actions)="data">
              <dashboard-row-actions
                :typeLabel="$t('ui.common.location')"
                :displayItem="data.item"
                :itemLabel="data.item.id"
                :id="data.item.id"
                detailIcon="dashboard-devices-id-details"
                editIcon="dashboard-devices-id-edit"
                deleteIcon="gateway/devices/delete"
                disableIcon="gateway/devices/enable"
                enableIcon="gateway/devices/disable"
              ></dashboard-row-actions>
            </template>
          </b-table>
          <dashboard-table-pagination
              tableName="indexTable2"
              tableIndex="2"
              position="bottom"
              :rowCount="dataCluster.length"
            >
          </dashboard-table-pagination>
        </b-tab>
      </b-tabs>
    </span>
  </dashboard-display-index>
</template>

<script>
  import Fuse from 'fuse.js';

  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";
  import { tabAnchorMixin } from "@/mixins/tabAnchorMixin";

  import { GW_Device } from '@/models/device'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin, tabAnchorMixin],
    data() {
      return {
        dashboardBusModel: "devices",
        tableColumns1: [
          {key: 'full_location', label: this.$i18n.t('ui.common.location') },
          {key: 'label', label: this.$i18n.t('ui.common.label') },
          {key: 'description',  label: this.$i18n.t('ui.common.description') },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ],
        tableColumns2: [
          {key: 'gateway_id', label: this.$i18n.t('ui.common.gateway') },
          {key: 'full_location', label: this.$i18n.t('ui.common.location') },
          {key: 'label', label: this.$i18n.t('ui.common.label') },
          {key: 'description',  label: this.$i18n.t('ui.common.description') },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ],
      }
    },
    computed: {
      dataLocal() {
        let that = this;
        return this.dashboardQueriedData.filter(data => data && data.gateway_id == this.gateway_id);
      },
      dataCluster() {
        return this.dashboardQueriedData.filter(data => data && data.gateway_id != this.gateway_id);
      },
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Device.query()
                                              .orderBy('full_label', 'asc')
                                              .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.7 },
            { name: 'full_label', weight: 0.2 },
            { name: 'description', weight: 0.1 },
          ]
        });
      }
    },
    mounted() {
      this.tabAnchorSetup(['#local', '#cluster']);
    }
  };
</script>
