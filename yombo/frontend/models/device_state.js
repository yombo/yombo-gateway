import { Model } from '@vuex-orm/core'

export class GW_Device_State extends Model {
  static entity = 'gw_device_states';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      gateway_id: this.string(''),
      device_id: this.string(''),
      command_id: this.string(''),
      device_command_id: this.string(''),
      energy_usage: this.number(0),
      energy_type: this.string(''),
      human_state: this.string(''),
      human_message: this.attr(''),
      machine_state: this.number(0),
      machine_state_extra: this.attr({}),
      request_by: this.string(''),
      request_by_type: this.string(''),
      request_context: this.string(''),
      reporting_source: this.string(''),
      created_at: this.string(''),
      uploaded: this.boolean(0),
      uploadable: this.boolean(0),
    }
  }
}
