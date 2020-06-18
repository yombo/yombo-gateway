import { Model } from '@vuex-orm/core'
import { GW_Location } from './location'
import { GW_Device_Command } from '@/models/device_command'
// import { Yombo_Gateway } from '@/models/gateway'

class Device extends Model {
  static entity = 'devices';

  static state()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      device_parent_id: this.string(''),
      gateway_id: this.string(''),
      user_id: this.string(''),
      device_type_id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      full_label: this.string('').nullable(),
      area_label: this.string('').nullable(),
      location_id: this.string('').nullable(),
      // location_id: this.morphMany(Location, 'id', 'location_type'),
      area_id: this.string('').nullable(),
      // area_id: this.hasOne(Location, 'id'),  // for some reason, this causes the value to be null. same w/ location_id
      notes: this.string('').nullable(),
      attributes: this.string('').nullable(),
      intent_allow: this.string('').nullable(),
      intent_text: this.string('').nullable(),
      pin_code: this.string('').nullable(),
      pin_required: this.boolean(0),
      pin_timeout: this.number(0).nullable(),
      statistic_type: this.string('').nullable(),
      statistic_label: this.string(''),
      statistic_lifetime: this.number(0),
      statistic_bucket_size: this.string('').nullable(),
      energy_type: this.string('').nullable(),
      energy_tracker_source_type: this.string('').nullable(),
      energy_tracker_source_id: this.string('').nullable(),
      energy_map: this.attr({0.0: 0, 1.0: 0}).nullable(),
      scene_controllable: this.boolean(0).nullable(),
      allow_direct_control: this.boolean('').nullable(),
      status: this.number(1),
      created_at: this.number(0),
      updated_at: this.number(0),
      device_features: this.attr({}).nullable(),
      device_mfg: this.string('').nullable(),
      device_model: this.string('').nullable(),
      device_platform: this.string('').nullable(),
      device_serial: this.string('').nullable(),
      device_sub_platform: this.string('').nullable(),
      system_disabled: this.boolean(0).nullable(),
      system_disabled_reason: this.string('').nullable(),
      is_direct_controllable: this.boolean(1).nullable(),
      is_allowed_in_scenes: this.boolean(1).nullable(),
      device_commands: this.hasMany(GW_Device_Command, 'device_id', 'id'),
    }
  }

  // get full_label () {
  //   // console.log("GW_Location:");
  //   // console.log(GW_Location);
  //   // console.log(`full_location: ${this.location_id}`);
  //   // console.log(Yombo_Gateway.all());
  //   // console.log(GW_Location.all());
  //   let location = GW_Location.find(this.location_id);
  //   let label = "";
  //   if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
  //     label += location.label + " ";
  //   }
  //   location = GW_Location.find(this.area_id);
  //   if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
  //     label += location.label + " ";
  //   }
  //   return `${label}${this.label}`
  // }

  get full_location () {
    // console.log(`full_location: ${this.location_id}`);
    let location = GW_Location.find(this.location_id);
    let label = "";
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label + " ";
    }
    location = GW_Location.find(this.area_id);
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label;
    }
    if (label.length == 0) {
      label = "Unknown"
    }
    return `${label.trim()}`
  }

  // get location_location () {
  //   let location = GW_Location.find(this.location_id);
  //   let label = "";
  //   if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
  //     label += location.label + " ";
  //   } else {
  //     label = this.location_id
  //   }
  //   return `${label.trim()}`
  // }
  //
  // get area_location () {
  //   let location = GW_Location.find(this.area_id);
  //   let label = "";
  //   if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
  //     label += location.label + " ";
  //   } else {
  //     label = this.area_id
  //   }
  //   return `${label.trim()}`
  // }
}

export class GW_Device extends Device {
  static entity = 'gw_devices';
}

export class Yombo_Device extends Device {
  static entity = 'yombo_devices';
}
