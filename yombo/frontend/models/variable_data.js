import { Model } from '@vuex-orm/core'

class Variable_Data extends Model {
  static entity = 'variable_data';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      gateway_id: this.string(''),
      variable_field_id: this.string(''),
      variable_relation_id: this.string(''),
      variable_relation_type: this.string(''),
      data: this.attr(null),
      data_content_type: this.string(null),
      data_weight: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Variable_Data extends Variable_Data {
  static entity = 'gw_variable_data';
}

export class Yombo_Variable_Data extends Variable_Data {
  static entity = 'yombo_variable_data';
}
