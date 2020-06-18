import { Model } from '@vuex-orm/core'

export class GW_Config extends Model {
  static entity = 'gw_configs';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      value: this.attr(''),
      value_type: this.string(''),
      fetches: this.number(''),
      writes: this.number(''),
      checksum: this.string(''),
      source: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
