import { Model } from '@vuex-orm/core'

export class GW_Role extends Model {
  static entity = 'gw_roles';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      request_by: this.string(''),
      request_by_type: this.string(''),
      request_context: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
