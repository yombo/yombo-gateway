import { Model } from '@vuex-orm/core'

class Variable_Field extends Model {
  static entity = 'variable_fields';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      variable_group_id: this.string(''),
      field_machine_label: this.string(''),
      field_label: this.string(''),
      field_description: this.string(''),
      field_weight: this.number(null),
      value_required: this.number(''),
      value_max: this.number(null),
      value_min: this.number(null),
      encryption: this.string(''),
      value_casing: this.string(''),
      input_type_id: this.string(''),
      default_value: this.string(''),
      field_help_text: this.string(''),
      multiple: this.number(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Variable_Field extends Variable_Field {
  static entity = 'gw_variable_fields';
}

export class Yombo_Variable_Field extends Variable_Field {
  static entity = 'yombo_variable_fields';
}
