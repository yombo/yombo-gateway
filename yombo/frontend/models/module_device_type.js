import { Model } from '@vuex-orm/core'

export default class Module_Device_type extends Model {
  static entity = 'module_device_type';

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      location_type: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
