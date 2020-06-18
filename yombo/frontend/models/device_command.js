import { Model } from '@vuex-orm/core'

import { GW_Command } from '@/models/command'
import { GW_Device } from '@/models/device'

export class GW_Device_Command extends Model {
  static entity = 'gw_device_commands';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      gateway_id: this.string(''),
      persistent_request_id: this.string(''),
      device_id: this.string(''),
      device: this.hasOne(GW_Device, 'id', 'command_id'),
      command_id: this.string(''),
      command: this.hasOne(GW_Command, 'id', 'command_id'),
      inputs: this.attr('').nullable(),
      created_at: this.number(''),
      broadcast_at: this.number('').nullable(),
      accepted_at: this.number('').nullable(),
      sent_at: this.number('').nullable(),
      received_at: this.number('').nullable(),
      pending_at: this.number('').nullable(),
      finished_at: this.number('').nullable(),
      not_before_at: this.number('').nullable(),
      not_after_at: this.number('').nullable(),
      history: this.attr('').nullable(),
      status: this.string(''),
      request_by: this.string(''),
      request_by_type: this.string(''),
      request_context: this.string(''),
      idempotence: this.string('').nullable(),
      uploaded: this.number(''),
      uploadable: this.number(''),
    }
  }
}
