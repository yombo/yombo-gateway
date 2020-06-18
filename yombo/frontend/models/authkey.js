import { Model } from '@vuex-orm/core'

export class GW_Authkey extends Model {
  static entity = 'gw_authkeys';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      auth_key_id_full: this.string(''),
      preserve_key: this.boolean(null),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      roles: this.attr({}),
      request_by: this.string(''),
      request_by_type: this.string(''),
      request_context: this.string(''),
      expired_at: this.number(0),
      last_access_at: this.number(0),
      status: this.number(null),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
