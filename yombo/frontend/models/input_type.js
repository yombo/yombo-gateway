import { Model } from '@vuex-orm/core'

export class Input_Type extends Model {
  static entity = 'input_types';

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

export class GW_Input_Type extends Input_Type {
  static entity = 'gw_input_types';
}

export class Yombo_Input_Type extends Input_Type {
  static entity = 'yombo_input_types';
}
