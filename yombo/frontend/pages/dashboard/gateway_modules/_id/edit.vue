<template>
  <div v-if="device">
    <card card-body-classes="table-full-width">
      <div slot="header">
      <h4 class="card-title">
         {{ $t('ui.common.edit') }} {{ $t('ui.common.device') }}: {{device.full_label}}
        <div class="pull-left">
          <nuxt-link :to="'/dashboard/devices/'+id+'/details'">
            <i class="fas fa-chevron-left"></i>
          </nuxt-link> &nbsp;

<!--          <action-details path="dashboard-devices" :id="device.id" size="regular"/>-->
<!--          <template v-if="device.status == 1">-->
<!--            <action-disable dispatch="yombo/devices/disable" :id="device.id"-->
<!--                         i18n="device" :item_label="device.full_label"-->
<!--                         size="regular"/>-->
<!--          </template>-->
<!--          <template v-else>-->
<!--            <action-enable dispatch="yombo/devices/enable" :id="device.id"-->
<!--                         i18n="device" :item_label="device.full_label"-->
<!--                         size="regular"/>-->
<!--          </template>-->
<!--          <action-delete dispatch="yombo/devices/delete" :id="device.id"-->
<!--           i18n="device" :item_label="device.full_label"-->
<!--           size="regular"/>-->
        </div>
       </h4>
      </div>
      <p></p>
      <div class="card-body">
        <b-form @submit="onSubmit" @reset="onReset">
          <div class="row">
            <div class="col">
              <div class="framed-content">
                <h4>Basic</h4>
                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Device Label:
                      <b-button v-b-modal.label variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-input v-model="device.label" required placeholder="Device label"></b-form-input>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Machine Label:
                      <b-button v-b-modal.machine_label variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-input v-model="device.machine_label" required placeholder="Set a machine_label."></b-form-input>
                    </b-form-group>
                  </div>
                </div>
                <b-form-group>
                  Description:
                  <b-button v-b-modal.description variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                  <b-form-input v-model="device.description" required placeholder="Description of device."></b-form-input>
                </b-form-group>

                <b-form-group>
                  Notes:
                  <b-button v-b-modal.notes variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                  <b-form-textarea
                    id="textarea"
                    v-model="device.notes"
                    placeholder="Device description..."
                    rows="3"
                    max-rows="6"
                  ></b-form-textarea>
                </b-form-group>

                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Location:
                      <b-button v-b-modal.location_id variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.location_id" :options="locations"></b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Area:
                      <b-button v-b-modal.area_id variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.area_id" :options="areas"></b-form-select>
                    </b-form-group>
                  </div>
                </div>
                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Parent Device:
                      <b-button v-b-modal.area_id variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.device_parent_id" :options="local_devices"></b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    Status:
                    <b-button v-b-modal.status variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                    <b-form-select v-model="device.status" label="Status:">
                      <b-form-select-option value="1">Enable</b-form-select-option>
                      <b-form-select-option value="0">Disable</b-form-select-option>
                      <b-form-select-option value="2">Delete</b-form-select-option>
                    </b-form-select>
                  </div>
                </div>
              </div>

              <div class="framed-content">
                <h4>Control</h4>
                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Scene Controllable:
                      <b-button v-b-modal.scene_controllable variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.scene_controllable">
                        <b-form-select-option value="true">Yes</b-form-select-option>
                        <b-form-select-option value="false">No</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Allow Direct Control:
                      <b-button v-b-modal.allow_direct_control variant="neutral" size="help">
                        <i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.allow_direct_control">
                        <b-form-select-option value="true">Yes</b-form-select-option>
                        <b-form-select-option value="false">No</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                </div>
                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Pin Required:
                      <b-button v-b-modal.pin_required variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.pin_required">
                        <b-form-select-option value="false">No</b-form-select-option>
                        <b-form-select-option value="true">Yes</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Pin Timeout:
                      <b-button v-b-modal.pin_code variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-input v-model="device.pin_timeout" required placeholder="Pin timeout, numbers only." type="number"></b-form-input>
                    </b-form-group>
                  </div>
                </div>
                <b-form-group>
                  Pin code:
                  <b-button v-b-modal.pin_code variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                  <b-form-input v-model="device.pin_code" required placeholder="Pin code"></b-form-input>
                </b-form-group>
              </div>

              <div class="framed-content">
                <h4>Statistics</h4>
                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Statistics Type:
                      <b-button v-b-modal.statistics_type variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.statistic_type">
                        <b-form-select-option value="none">None</b-form-select-option>
                        <b-form-select-option value="datapoint">Data point</b-form-select-option>
                        <b-form-select-option value="average">Average</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    <b-form-group v-if="device.statistic_type !== 'none'">
                      Statistic Label:
                      <b-button v-b-modal.statistic_label variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-input v-on:blur="statisticsLabelBlur" v-model="device.statistic_label" required placeholder="Device label"></b-form-input>
                    </b-form-group>
                  </div>
                </div>

                <div class="row col-nested" v-if="device.statistic_type === 'average'">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Statistics Lifetime:
                      <b-button v-b-modal.statistic_lifetime variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.statistic_lifetime">
                        <b-form-select-option value="none">None</b-form-select-option>
                        <b-form-select-option value="datapoint">Data point</b-form-select-option>
                        <b-form-select-option value="average">Average</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Statistic Bucket Size:
                      <b-button v-b-modal.statistic_bucket_size variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-input v-model="device.statistic_bucket_size" required placeholder="Statistic Bucket Size"></b-form-input>
                    </b-form-group>
                  </div>
                </div>
              </div>

              <div class="framed-content">
                <h4>Energy Information</h4>
                <div class="row col-nested">
                  <div class="col-md-12 col-lg-6">
                    <b-form-group>
                      Energy Type:
                      <b-button v-b-modal.energy_type variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.energy_type">
                        <b-form-select-option value="none">None</b-form-select-option>
                        <b-form-select-option value="electric">Electric</b-form-select-option>
                        <b-form-select-option value="gas">Gas</b-form-select-option>
                        <b-form-select-option value="water">Water</b-form-select-option>
                        <b-form-select-option value="noise">Noise</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                  <div class="col-md-12 col-lg-6" v-if="device.energy_type !== 'none'">
                    <b-form-group>
                      Energy Info Source Type:
                      <b-button v-b-modal.energy_tracker_source_type variant="neutral" size="help">
                        <i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                      <b-form-select v-model="device.energy_tracker_source_type">
                        <b-form-select-option value="calculated">Calculated</b-form-select-option>
                        <b-form-select-option value="device">Device</b-form-select-option>
                        <b-form-select-option value="state">State</b-form-select-option>
                      </b-form-select>
                    </b-form-group>
                  </div>
                </div>
                <div v-if="device.energy_type !== 'none'">
                  <b-form-group v-if="device.energy_tracker_source_type === 'calculated'">
                    Energy Map Device (To be completed):
                    <b-button v-b-modal.energy_map variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
<!--                    <b-form-input v-model="device.energy_map" required placeholder="Energy Map Array"></b-form-input>-->
<!--                    <div class="row col-nested" v-for="(item, index) in device.energy_map">-->
<!--                      <div class="col-md-12 col-lg-6">-->
<!--                        item: {{typeof item}} {{item}}<br>-->
<!--                        index: {{typeof index}} {{index}}<br>-->
<!--                        device.energy_map: {{typeof device.energy_map[index]}} {{device.energy_map[index]}}<br>-->
<!--                        <b-form-input v-model="index" required placeholder="Energy Map Percent"></b-form-input>-->
<!--                      </div>-->
<!--                      <div class="col-md-12 col-lg-6">-->
<!--                        <b-form-input v-model="new_energy_map[index]" required placeholder="Energy Map Value"></b-form-input>-->
<!--                      </div>-->
<!--                    </div>-->
                  </b-form-group>
                  <b-form-group v-if="device.energy_tracker_source_type === 'device'">
                    Energy Source Device:
                    <b-button v-b-modal.energy_tracker_source_id variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                    <b-form-select v-model="device.energy_tracker_source_id" :options="local_devices"></b-form-select>
                  </b-form-group>
                  <b-form-group v-else-if="device.energy_tracker_source_type === 'state'">
                    Energy Source State:
                    <b-button v-b-modal.energy_tracker_source_id variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                    <b-form-input v-model="device.energy_tracker_source_id" required placeholder="State name."></b-form-input>
                  </b-form-group>
                </div>

              </div>
              <b-button type="reset" variant="danger">Reset</b-button>
              <b-button type="submit" variant="success">Submit</b-button>
            </div>
          </div>
        </b-form>
        <b-card class="mt-3" header="Form Data Result">
          <pre class="m-0">{{ device }}</pre>
        </b-card>
      </div>
    </card>

    <b-modal id="label" title="Label">
      <p>
        A label for the device to easily identify it.
      </p>
    </b-modal>
    <b-modal id="machine_label" title="Machine Label">
      <p>
        This label is used to uniquely identify this device across all locations and areas. For example,
        if you have two houses (lucky you), each having two dens, you want want to label this device
        something like 'vacation_house_den_light', while the 'Label' would simply be 'Light'.
      </p>
      <p>
        The machine label is used within rules and custom automation modules lookup the device by name,
        rather than it's ID.
      </p>
    </b-modal>
    <b-modal id="description" title="Description">
      <p>
        Provide short description about the device to remind yourself what it does.
      </p>
    </b-modal>
    <b-modal id="notes" title="Notes">
      <p>
        Add extended notes about the device.
      </p>
    </b-modal>
    <b-modal id="location_id" title="Location">
      <p>
        What building or location the device is in. Such as house, shed, guest house, etc.
      </p>
    </b-modal>
    <b-modal id="area_id" title="Area">
      <p>
        What area within the location the device is located. Such as bedroom, living room, patio, etc.
      </p>
    </b-modal>
    <b-modal id="pin_required" title="Pin Required">
      <p>
        If yes, a pin is required to control the device.
      </p>
    </b-modal>
    <b-modal id="pin_code" title="Pin Code">
      <p>
        A code for the device. If pin required is true, and this field is blank, the user's account pin
        will be accepted.
      </p>
    </b-modal>
    <b-modal id="pin_timeout" title="Pin Timeout">
      <p>
        Time pin code is remembered. Once you've entered a pin, you will be authorized to perform
        another function on the device unless the timeout has elapsed.
      </p>
    </b-modal>
    <b-modal id="scene_controllable" title="Scene Controllable">
      <p>
        If true, scenes and automation rules are able to control the device. This is a safety settings
        so that scenes can't accidentally control devices that shouldn't be controlled automatically.
        Typically this includes gateway, doors, etc.
      </p>
    </b-modal>
    <b-modal id="allow_direct_control" title="Allow Direct Control">
      <p>
        If true, allows users to directly control this device. This should should set to false for items like
        relays that should only be controlled by modules, scenes, or automation rules.
      </p>
    </b-modal>
    <b-modal id="device_parent_id" title="Status">
      <p>
        You can enable or disable the device as needed. When disabled, the device cannot receive commands
        or send status updates. When deleted, the device will eventually be purged from the Yombo system.
      </p>
    </b-modal>
    <b-modal id="status" title="Status">
      <p>
        You can enable or disable the device as needed. When disabled, the device cannot receive commands
        or send status updates. When deleted, the device will eventually be purged from the Yombo system.
      </p>
    </b-modal>
    <b-modal id="statistic_type" title="Status">
      <p>
        You can enable or disable the device as needed. When disabled, the device cannot receive commands
        or send status updates. When deleted, the device will eventually be purged from the Yombo system.
      </p>
    </b-modal>
    <b-modal id="statistics_type" title="Statistics Type">
      <p>There are two primary statistics:</p>
      <ul>
          <li>Data Point - A single data point such as if the window is closed or open, light on, 50% or off.</li>
          <li>Average - Can average data points together. This is the best way to store temperature data or
          other inputs that tend to flucuate a alot. This also helps keeps your database file from getting
          to big.</li>
          <ul>
              <li>When using the average method, you also need to set the 'bucket size', or how long
                  the data should be averaged together. For example, a bucket size of '60' will average data
                  together for 60 seconds.  See 'bucket size' for details.</li>
          </ul>
      </ul>
    </b-modal>
    <b-modal id="statistic_label" title="Statistics Label">
      <p>
        The default statistic label uses the 'location + area + machine_name' for the device if no
        value is set.</p>
      <p>This label is used to track the device history over time. Using a label allows the device to be replaced with
      a new device, but still maintain it's history. For example,
      if you have an insteon lamp module controlling your living table lamp and later decide to replace with zwave, you would give
      the device name the same statistic label.</p>
      <p>The statistic label is free form.</p>
      <p>You will want to name the location from least specific to most specific using a dotted notation, such as
      'myhouse.downstairs.livingroom.tabel_lamp'.  If you didn't have two stories, just omit 'downstairs'.</p>
      <p>Some more examples:</p>
      <ul>
          <li>house.garage.workbench_light</li>
          <li>house.master_bedroom.ceiling_fan</li>
          <li>house.kitchen.fan</li>
          <li>house.hvac</li>
          <li>house.patio.landscape_lights</li>
          <li>house.garden.landscape_sprinklers</li>
          <li>house.all.music</li>
      </ul>
      <p>
        After some statistics are generated, you can show energy/water/noise for any given area. For example,
      you show all water used 'outside.*' or 'outside.front' for a given time period. Or electricity used
      with search terms like 'myhouse.upstairs.* or 'myhouse.*.bedroom'.
      </p>
      <p> <strong>Note:</strong> All statistic labels are preceeded with 'devices.' to help with tracking
          various other system statistics. Additionally, another statistic with 'energy.' will be used
          to track enery usage for this device.
      </p>
    </b-modal>
    <b-modal id="statistic_lifetime" title="Statistic Lifetime">
      <p>
        How long (in days) the statistic or status information should stay in the local database. Keeping
        statistics locally for long periods of time can be cause the local database to become rather large.
        We recommend keeping this to under a year, and using the Yombo Online Statistics tools to track
        historical data.
      </p>
    </b-modal>
    <b-modal id="statistic_bucket_size" title="Statistic Bucket Size">
      <p>
        When averaging data points together, the system divides time into 'buckets' For example, if 60 seconds is
        set as the bucket set, all data points within a 60 second will be grouped together.
     </p>
    </b-modal>

    <b-modal id="energy_type" title="Energy Type">
      <p>
        Allows you to track energy various types of energy or consumables consumed or produced by by this device.
      </p>
    </b-modal>
    <b-modal id="energy_tracker_source_type" title="Energy Tracker Source Type">
      <p>
        Energy information can be collected from various sources. Some modules that manage a device will
        override this setting, as is the case for many thermostats.
      </p>
      <ul>
        <li>Calculated - Use the energy map below to calculate usage. Most commong for basic devices.</li>
        <li>Device - Allows a device to specified. It's machine status value will be used as the energy value.</li>
        <li>State - A state's value will be used as the energy value.</li>
      </ul>
    </b-modal>
    <b-modal id="energy_tracker_source_id" title="Energy Tracker Source ID">
      <p>
        Define the source energy status. If 'source type' is set to state, the state name value will be used. If
        it's a device, the device's machine_state value will be used.
      </p>
      <p>
        <em>The value of the state or device's machine_state must be either an integer or float.</em>
      </p>
    </b-modal>
    <b-modal id="energy_map" title="Energy Map">
      <p>
        Allows you to specify ranges of energy consumption or generation for any particular device, including
        water usage. With an energy 'map', Yombo Gateway can calculate the energy usage (or generation) for a
        particular device. For example, if a lamp module is on 25%, it will calculate how much energy is being
        consumed at 25% power.
      </p>
      <p>
        Typically, you will have 0% and 100%. For 0%, you might put 1 or 2 watts as most insteon,
        zwave, x10 devices consume some power all the time, regardless of the state. For 100%, you would put in
        the bulb usage power plus the 0% rate. So, for a 40 watt bulb, you would enter 41 or 42.
      </p>
      <h3>Advanced use</h3>
      <p>
        The 'map' feature allows you to be very precise. For example, if your device consumes more power at lower
        set states (for exaple, at 25% on, it consumes relatively more power than at 40%). You can then specify that from
        0% to %50, the device can consume up 200 watts, but from 51% to 100%, it can consume up to 300 watts. In this
        example, a device at 25% power would consume 100 watts, but at 75%, it would consume 250watts.
     </p>
    </b-modal>

  </div>
</template>
<script>
import { ActionDelete, ActionDetails, ActionDisable, ActionEnable } from '@/components/Dashboard/Actions';
// import VSelect from "@alfsnd/vue-bootstrap-select";
import { GW_Device } from '@/models/device'
import { GW_Location } from '@/models/location'

export default {
  layout: 'dashboard',
  components: {
    ActionDelete,
    ActionDetails,
    ActionDisable,
    ActionEnable,
    // VSelect,
  },
  data() {
    return {
      id: this.$route.params.id,
      display_age: '0 seconds',
      device: null,
      generated_statistic_label: null,
    };
  },
  computed: {
    areas() {
      return this.convertToSelect(Location.query().where('location_type', 'area').orderBy('label', 'asc').get());
    },
    locations() {
      return this.convertToSelect(Location.query().where('location_type', 'location').orderBy('label', 'asc').get());
    },
    local_devices() {
      let local_devices = this.convertToSelect(Device.query()
                                             .where('gateway_id', this.device.gateway_id)
                                             .orderBy('full_label', 'asc')
                                             .get(), "full_label");
      local_devices.unshift({ value: null, text: "None"});
      return local_devices;
    },
    systemInfo: function () {
      return this.$store.state.gateway.systeminfo;
    },
  },
  watch: {
    'device.allow_direct_control': function (newVal, oldVal) {
      if (newVal == oldVal) return;
      if (newVal == "true") this.device.allow_direct_control = true;
      if (newVal == "false") this.device.allow_direct_control = false;
    },
    'device.scene_controllable': function (newVal, oldVal) {
      if (newVal == oldVal) return;
      if (newVal == "true") this.device.scene_controllable = true;
      if (newVal == "false") this.device.scene_controllable = false;
    },
    'device.pin_required': function (newVal, oldVal) {
      if (newVal == oldVal) return;
      if (newVal == "true") this.device.pin_required = true;
      if (newVal == "false") this.device.pin_required = false;
    },
    'device.label': function (newVal, oldVal) {
      console.log(`device.label 1. newVal: ${newVal}, oldVal: ${oldVal} `);
      if (oldVal == this.device.statistic_label || this.device.statistic_label == "" ||
          this.device.statistic_label == null || this.device.statistic_label == "null" )
        this.device.statistic_label = null;
      this.generateStatisticsLabel();
    },
    'device.area_id': function (newVal, oldVal) {
      console.log("device.area_id 1");
      this.generateStatisticsLabel()
    },
    'device.location_id': function (newVal, oldVal) {
      console.log("device.location_id 1");
      this.generateStatisticsLabel()
    },
    'device.energy_type': function (newVal, oldVal) {
      // if (this.device.energy_map == null || this.device.energy_map === "" || this.device.energy_map === "{}"
      // if (newVal == oldVal) return;
      // if (newVal == "true") this.device.allow_direct_control = true;
      // if (newVal == "false") this.device.allow_direct_control = false;
    },

  },
  methods: {
    statisticsLabelBlur() {
      this.generateStatisticsLabel()
    },
    generateStatisticsLabel(test = false) {
      console.log(`generateStatisticsLabel, static label: ${this.device.statistic_label}`);
      console.log(`generateStatisticsLabel, generated_statistic_label: ${this.generated_statistic_label}`);
      if (this.generated_statistic_label || this.device.statistic_label == null) {
       console.log(`generateStatisticsLabel, doing it`);
        let new_label = [];
        if (this.device.location_id !== "area_none" && this.device.location_id != null && this.device.location_id !== "") {
          let location = Location.query().where("id", this.device.location_id).first();
          if (location != null && location.machine_label !== "" && location.machine_label !== "none") {
            new_label.push(location.machine_label);
          }
        }
        if (this.device.area_id !== "area_none" && this.device.area_id != null && this.device.area_id !== "") {
          let location = Location.query().where("id", this.device.area_id).first();
          console.log("area location:");
          console.log(location);
          if (location != null) {
            new_label.push(location.machine_label);
          }
        }
        new_label.push(this.device.label);
        console.log("GSL 5");
        let new_string = new_label.join(".").replace(" ", "_").toLowerCase();
        console.log("GSL 6: " + new_string);
        if (test === true)
          return new_string;
        this.device.statistic_label = new_string;
        this.generated_statistic_label = true;
        console.log("GSL 7");
      }
    },
    onSubmit(evt) {
        evt.preventDefault();
        alert(JSON.stringify(this.device));
      },
    onReset(evt = null) {
        evt.preventDefault();
        this.device = Device.query().where('id', this.id).first();
      },
    convertToSelect(locations, text_field = "label") {
      let results = [];
      let location = null;
      for (let index = 0; index < locations.length; index++) {
        location = locations[index];
        results.push({
          value: location.id,
          text: location[text_field],
        });
      }
      return results;
    },
  },
  beforeCreate() {
    this.$store.dispatch('gateway/devices/fetchOne', this.id);
  },
  created() {
    this.device = Device.query().where('id', this.id).first();
    this.generated_statistic_label = this.generateStatisticsLabel() === this.device.statistic_label;
  },
  mounted () {
    this.$bus.$emit("listenerUpdateBreadcrumb",
      {index: 2, path: "dashboard-devices-id-details", props: {id: this.id}, text: this.device.label});
    this.$bus.$emit("listenerDeleteBreadcrumb", 3);
    this.$bus.$emit("listenerAppendBreadcrumb",
      {index: 2, path: "dashboard-devices-id-edit", props: {id: this.id}, text: "ui.navigation.edit"});
  },
};
</script>
