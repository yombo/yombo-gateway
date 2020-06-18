import { Model } from '@vuex-orm/core'

export class Device_Type extends Model {
  static entity = 'device_types';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      original_user_id: this.string(''),
      category_id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      is_usable: this.boolean(true),
      public: this.number(0),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Device_Type extends Device_Type {
  static entity = 'gw_device_types';
}

export class Yombo_Device_Type extends Device_Type {
  static entity = 'yombo_device_types';
}
