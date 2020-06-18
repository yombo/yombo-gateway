import { Model } from '@vuex-orm/core'

export class Atom extends Model {
  static entity = 'atoms';

  static state () {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      gateway_id: this.string(''),
      value: this.attr(''),
      value_type: this.attr(null),
      value_human: this.attr(''),
      request_by: this.string(''),
      request_by_type: this.string(''),
      request_context: this.string(''),
      last_access_at: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Atom extends Atom {
  static entity = 'gw_atoms';
}

export class Yombo_Atom extends Atom {
  static entity = 'yombo_atoms';
}
