import { Model } from '@vuex-orm/core'

import { GW_Command, Yombo_Command } from '@/models/command'
import { GW_Device_Type, Yombo_Device_Type } from '@/models/device_type'
import { GW_Input_Type, Yombo_Input_Type } from '@/models/input_type'

export class Device_Command_Input extends Model {
  static entity = 'device_command_inputs';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static additional_fields() {
    return {}
  }

  static fields () {
    return {
      id: this.string(''),
      device_type_id: this.string(''),
      command_id: this.string(''),
      input_type_id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      live_update: this.number(0),
      value_required: this.number(0),
      value_max: this.number(0),
      value_min: this.number(0),
      value_casing: this.string(''),
      encryption: this.string(''),
      notes: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
      ...this.additional_fields(),
    }
  }
}

export class GW_Device_Command_Input extends Device_Command_Input {
  static entity = 'gw_device_command_inputs';

  static additional_fields() {
    return {
      device_type: this.hasOne(GW_Device_Type, 'id', 'device_type_id'),
      command: this.hasOne(GW_Command, 'id', 'command_id'),
      input_type: this.hasOne(GW_Input_Type, 'id', 'input_type_id'),
    }
  }
}

export class Yombo_Device_Command_Input extends Device_Command_Input {
  static entity = 'yombo_device_command_inputs';

  additional_fields() {
    return {
      device_type: this.hasOne(Yombo_Device_Type, 'id', 'device_type_id'),
      command: this.hasOne(Yombo_Command, 'id', 'command_id'),
      input_type: this.hasOne(Yombo_Input_Type, 'id', 'input_type_id'),
    }
  }
}
