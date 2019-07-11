import { Model } from '@vuex-orm/core'

import Command from '@/models/command'

export default class Device_Command extends Model {
  static entity = 'device_commands';

  static fields () {
    return {
      id: this.string(''),
      device_id: this.string(''),
      command_id: this.string(''),
      command: this.hasOne(Command, 'id', 'command_id')
    }
  }
}
