import { Model } from '@vuex-orm/core'

export default class Device_Type_Command extends Model {
  static entity = 'device_type_commands';

  static fields () {
    return {
      id: this.string(''),
      device_type_id: this.string(''),
      command_id: this.string(''),
      created_at: this.number(0),
    }
  }
}
