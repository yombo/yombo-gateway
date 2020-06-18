import { Model } from '@vuex-orm/core'

export class Module_Device_Type extends Model {
  static entity = 'module_device_type';

  static state ()  {
    return {
      api_source: null,
    }
  }

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

export class GW_Module_Device_Type extends Module_Device_Type {
  static entity = 'gw_module_device_type';
}

export class Yombo_Module_Device_Type extends Module_Device_Type {
  static entity = 'yombo_module_device_type';
}
