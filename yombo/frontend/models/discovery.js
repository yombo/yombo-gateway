import { Model } from '@vuex-orm/core'
// import {GW_Device_Type_Command} from "./device_type_command";

export class GW_Discovery extends Model {
  static entity = 'gw_discovery';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      gateway_id: this.string(''),
      device_id: this.string('').nullable(),
      device_type_id: this.string('').nullable(),
      discovered_at: this.number(0),
      last_seen_at: this.number(0),
      mfr: this.string(''),
      model: this.string(''),
      serial: this.string(''),
      label: this.string('').nullable(),
      machine_label: this.string('').nullable(),
      description: this.string('').nullable(),
      variables: this.attr('').nullable(),
      request_context: this.string(''),
      status: this.number(1),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
