<template>
  <span>
    <div class="card-body builtin-ct">
      <dashboard-display-data :displayItem="data_ready" :apiErrors="apiErrors">
        <div class="bd-highlight" v-if="$parent.$parent.apiErrors == null">
          <fg-input>
            <el-input type="search"
                      class="mb-0"
                      clearable
                      prefix-icon="el-icon-search"
                      style="width: 200px"
                      :placeholder="$t('ui.common.search_ddd')"
                      v-model="dashboardSearchQuery"
                      aria-controls="datatables">
            </el-input>
          </fg-input>
        </div>

        <div v-if="data_ready" class="row row-state mx-1" v-for='(deviceGroup, groupIndex) in deviceGroups'>
            <div class="col-md-6 col-lg-3" v-for='(device, index) in deviceGroup'>
<!--              {{device.full_label}}-->
              <generic-card :device="device"
                            :commands="device_commands(device.device_type_id)"
                            :state="device_state(device.id)"></generic-card>
            </div>
        </div>
      </dashboard-display-data>
    </div>
  </span>
</template>

<script>
  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";
  import DashboardDisplayData from '@/components/Dashboard/DashboardDisplayData.vue';

  import GenericCard from '@/components/ControlTower/Cards/generic';
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
    },
    data() {
      return {
        itemsPerRow: 4,
        device_commands_cache: {},
        device_states: {},
        devices: [],
        commands_ready: false,
        device_states_ready: false,
        device_commands_ready: false,
        device_type_commands_ready: false,
      };
    },
    computed: {
      deviceGroups () {
        let devices = this.dashboardDisplayItems;
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
      data_ready () {
        if (this.dashboardDisplayItems == null || this.commands_ready == false || this.device_states_ready == false ||
          this.device_commands_ready == false || this.device_type_commands_ready == false ) {
          return null;
        }
        return true
      }
    },
    methods: {
      device_state: function(device_id) {
        return GW_Device_State.query().with('commands').where('device_id', device_id).first();
      },
      device_commands: function(device_type_id) {
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

          // Get devices
          this.$store.dispatch(`gateway/devices/${fetchType}`)
            .then(function() {
              that.dashboardDisplayItems = GW_Device.query()
                                           .orderBy('full_label', 'asc')
                                           .get();
              that.dashboardFuseSearch = new Fuse(that.dashboardDisplayItems, {
                keys: [
                  { name: 'full_label', weight: 0.7 },
                  { name: 'description', weight: 0.3 },
                ]
              });
            })
            .catch(error => {
              that.apiErrors = this.$handleApiErrorResponse(error, this.apiErrors);
            });

          // Get commands
          this.$store.dispatch(`gateway/commands/${fetchType}`)
            .then(function() {
              that.commands_ready = true;
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

        }
    },
    mounted () {
      this.$store.dispatch('gateway/locations/refresh');
    },
  };
</script>

<style scoped>
  .builtin-ct {
    background-color: #1C3B60 !important;
  }

  .card-body {
    padding: .9rem;
  }
</style>
