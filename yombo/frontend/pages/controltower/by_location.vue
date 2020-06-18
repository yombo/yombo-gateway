<template>
  <div class="container-fluid local-body">
    <portal to="topnavbar">
      {{ metaPageTitle }}
    </portal>
    <dashboard-display-data :displayItem="dataReady" :apiErrors="apiErrors">
      <div class="card-body builtin-ct">
        <b-container fluid>
          <b-row>
            <b-col>
              <multiselect v-model="location_selected" track-by="id" label="label"
                           :options="locations" :searchable="true"
                           :max-height="1000"
                           placeholder="Select a location"></multiselect>
            </b-col>
            <b-col>
              <multiselect v-model="area_selected" track-by="id" label="label"
                             :options="areas" :searchable="true"
                             :max-height="1000"
                             placeholder="Select an area"></multiselect>
            </b-col>
            <b-col md="auto">
              <div class="bd-highlight">
                <fg-input>
                  <el-input type="search"
                            class="mb-0b bg-white"
                            clearable
                            prefix-icon="el-icon-search"
                            style="width: 200px"
                            :placeholder="$t('ui.common.filter_ddd')"
                            v-model="dashboardSearchQuery"
                            aria-controls="datatables">
                  </el-input>
                </fg-input>
              </div>
            </b-col>
          </b-row>
        </b-container>
        <div v-if="userSetLocation" class="mt-4 ">
          <card class="builtin-inside-ct" card-body-classes="table-full-width">
            <div class="card-body builtin-inside-ct">
              <div class="row" v-for='(deviceGroup, groupIndex) in deviceGroups()'>
                <div class="col-md-6 col-lg-3" v-for='(device, index) in deviceGroup'>
                  <generic-card :device="device"
                                :commands="deviceCommands(device.device_type_id)"
                                :state="deviceState(device.id)"></generic-card>
                </div>
              </div>
            </div>
          </card>
        </div>
        <div v-else class="mt-4">
          <card card-body-classes="table-full-width builtin-inside-ct">
            <div slot="header">
              <h4 class="card-title">
                Select location and area
               </h4>
              </div>
            <div class="card-body">
              Select location and area to display devices.
            </div>
          </card>
        </div>
      </div>
    </dashboard-display-data>
  </div>
</template>

<script>
  import Multiselect from 'vue-multiselect'
  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";

  import DashboardDisplayData from '@/components/Dashboard/DashboardDisplayData.vue';
  import GenericCard from '@/components/ControlTower/Cards/generic';
  import { GW_Location } from '@/models/location';
  import { GW_Device } from '@/models/device';
  import { GW_Device_Type_Command } from '@/models/device_type_command';
  import { GW_Device_State } from '@/models/device_state';
  import Fuse from 'fuse.js'

  export default {
    layout: 'controltower',
    mixins: [dashboardApiIndexMixin],
    components: {
      DashboardDisplayData,
      GenericCard,
      Multiselect,
    },
    data() {
      return {
        metaPageTitle: this.$t('ui.navigation.by_location'), // set within commonMixin

        // API call status.
        commands_ready: false,
        devices_ready: false,
        device_commands_ready: false,
        device_states_ready: false,
        device_type_commands_ready: false,
        locations_ready: false,

        // Used for laying out devices.
        itemsPerRow: 4,
        device_commands_cache: {},
        device_states: {},
        devices: [],

        // Location selections
        location_selected: null,
        area_selected: null,

      };
    },
    computed: {
      locations() {
        let locations = GW_Location.query().where('location_type', 'location').orderBy('label', 'asc').get();
        locations.unshift({id: "__all__", label: "All"});
        return locations;
      },
      areas() {
        let areas = GW_Location.query().where('location_type', 'area').orderBy('label', 'asc').get();
        areas.unshift({id: "__all__", label: "All"});
        return areas;

      },
      dataReady() {
        if (this.commands_ready == null || this.devices_ready == false || this.device_commands_ready == false ||
          this.device_states_ready == false || this.device_type_commands_ready == false ||
          this.locations_ready == false ) {
          return null;
        }
        return true
      },
      userSetLocation() {
        console.log("########################### userSetLocation start");
        this.dashboardSearchQuery = "";

        if (this.location_selected !== null && this.area_selected !== null) {
          console.log("########################### userSetLocation, getting display items.");
          let query =  GW_Device.query();
          if (this.location_selected.id !== '__all__') {
            query = query.where('location_id', this.location_selected.id);
          }
          if (this.area_selected.id !== '__all__') {
            query = query.where('area_id', this.area_selected.id);
          }
          this.dashboardDisplayItems = query.orderBy('full_label', 'asc').get();
          this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
            keys: [
              { name: 'label', weight: 0.7 },
              { name: 'full_label', weight: 0.2 },
              { name: 'description', weight: 0.1 },
            ]
          });

          return true;
        }
        console.log("########################### userSetLocation - location not set, resetting defaults...");

        this.dashboardDisplayItems = null;
        this.dashboardFuseSearch = null;
        this.dashboardSearchedData = [];
        return false;
      }
    },
    methods: {
      deviceGroups() {
        console.log("########################### device groups start");
        let devices = this.dashboardQueriedData;
        if (devices == null) {
          return [];
        }
        let rows = Math.ceil(devices.length/this.itemsPerRow);
        let newArr = [];
        for (let rowNumber=0; rowNumber < rows; rowNumber+=1) {
          newArr.push(devices.slice(rowNumber*this.itemsPerRow, (rowNumber*this.itemsPerRow)+this.itemsPerRow));
        }
        return newArr;
      },
      deviceState(device_id) {
        return GW_Device_State.query().with('commands').where('device_id', device_id).first();
      },
      deviceCommands: function(device_type_id) {
        if (device_type_id in this.device_commands_cache) {
          return this.device_commands_cache[device_type_id];
        }

        let device_type_commands = GW_Device_Type_Command.query().with('command').where('device_type_id', device_type_id).get();
        let commands = {};
        device_type_commands.forEach(device_type_command => {
            commands[device_type_command.command_id] = device_type_command.command;
        });
        this.device_commands_cache[device_type_id] = commands;
        return commands;
      },
      dashboardFetchData(forceFetch = true) {
          let that = this;
          this.apiErrors = null;
          let fetchType = "refresh";
          if (forceFetch)
            fetchType = "fetch";

          // Get commands
          this.$store.dispatch(`gateway/commands/${fetchType}`)
            .then(function() {
              that.commands_ready = true;
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });

          // Get devices
          this.$store.dispatch(`gateway/devices/${fetchType}`)
            .then(function() {
              that.devices_ready = true;
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });

          // Get device_commands
          this.$store.dispatch(`gateway/device_commands/${fetchType}`)
            .then(function() {
              that.device_commands_ready = true;
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });

          // Get device states
          this.$store.dispatch(`gateway/device_states/${fetchType}`)
            .then(function() {
              that.device_states_ready = true;
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });

          // Get device_type_commands
          this.$store.dispatch(`gateway/device_type_commands/${fetchType}`)
            .then(function() {
              that.device_type_commands_ready = true;
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });

          // Get locations
          this.$store.dispatch(`gateway/locations/${fetchType}`)
            .then(function() {
              that.locations_ready = true;
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });
        }
    },
  };
</script>

<style scoped>
  .builtin-ct {
    background-color: #1C3B60 !important;
  }
  .builtin-inside-ct {
    background-color: #22466E !important;
  }

  .local-body { height: auto; margin: 0px; padding: 0px; }

</style>
