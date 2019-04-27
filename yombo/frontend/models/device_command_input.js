import { Model } from '@vuex-orm/core'

export default class Device_Command_Input extends Model {
  static entity = 'device_command_inputs';

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
      encryption: this.string(''),
      value_casing: this.string(''),
      notes: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
