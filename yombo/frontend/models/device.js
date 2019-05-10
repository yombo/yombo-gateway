import { Model } from '@vuex-orm/core'
import Location from './location'

export default class Device extends Model {
  static entity = 'devices';

  static fields () {
    return {
      id: this.string(''),
      gateway_id: this.string(''),
      user_id: this.string(''),
      device_type_id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      area_id: this.string('').nullable(),
      // area_id: this.hasOne(Location, 'id'),  // for some reason, this causes the value to be null. same w/ location_id
      location_id: this.string('').nullable(),
      // location_id: this.morphMany(Location, 'id', 'location_type'),
      notes: this.string('').nullable(),
      attributes: this.string('').nullable(),
      intent_allow: this.string('').nullable(),
      intent_text: this.string('').nullable(),
      pin_code: this.string('').nullable(),
      pin_required: this.number(0),
      pin_timeout: this.number(0).nullable(),
      statistic_label: this.string(''),
      statistic_lifetime: this.number(0),
      statistic_type: this.string(''),
      statistic_bucket_size: this.string('').nullable(),
      status_set_at: this.number(0).nullable(),
      energy_usage: this.number(0).nullable(),
      machine_status: this.number(0).nullable(),
      machine_status_extra: this.string('').nullable(),
      energy_tracker_source: this.string('').nullable(),
      energy_tracker_device_id: this.string('').nullable(),
      energy_map: this.string('').nullable(),
      controllable: this.number(0).nullable(),
      allow_direct_control: this.string('').nullable(),
      status: this.number(1),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }

  get full_label () {
    let location = Location.find(this.location_id);
    let label = "";
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label + " ";
    }
    location = Location.find(this.area_id);
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label + " ";
    }
    return `${label}${this.label}`
  }

  get full_location () {
    let location = Location.find(this.location_id);
    let label = "";
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label + " ";
    }
    location = Location.find(this.area_id);
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label;
    }
    if (label.length == 0) {
      label = "Unknwon"
    }
    return `${label.trim()}`
  }

  get location_location () {
    let location = Location.find(this.location_id);
    let label = "";
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label + " ";
    } else {
      label = this.location_id
    }
    return `${label.trim()}`
  }

  get area_location () {
    let location = Location.find(this.area_id);
    let label = "";
    if (location !== undefined && location != null && location.label.toLowerCase() != "none") {
      label += location.label + " ";
    } else {
      label = this.area_id
    }
    return `${label.trim()}`
  }

}
