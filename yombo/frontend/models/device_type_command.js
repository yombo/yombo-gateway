import { Base_Model } from '@/models/base_model'

import { GW_Command } from '@/models/command'

export class Device_Type_Command extends Base_Model {
  static entity = 'device_type_commands';

  static fields () {
    return {
      id: this.string(''),
      device_type_id: this.string(''),
      command_id: this.string(''),
      command: this.hasOne(GW_Command, 'id', 'command_id'),
      created_at: this.number(0),
    }
  }
}

export class GW_Device_Type_Command extends Device_Type_Command {
  static entity = 'gw_device_type_commands';
}

export class Yombo_Device_Type_Command extends Device_Type_Command {
  static entity = 'yombo_device_type_commands';
}
