import { Model } from '@vuex-orm/core'

class Variable_Group extends Model {
  static entity = 'variable_groups';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      group_relation_id: this.string(''),
      group_relation_type: this.string(''),
      group_machine_label: this.string(''),
      group_label: this.string(''),
      group_description: this.string(null),
      group_weight: this.number(''),
      status: this.string(null),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Variable_Group extends Variable_Group {
  static entity = 'gw_variable_groups';
}

export class Yombo_Variable_Group extends Variable_Group {
  static entity = 'yombo_variable_groups';
}
