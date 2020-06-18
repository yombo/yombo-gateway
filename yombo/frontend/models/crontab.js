import { Model } from '@vuex-orm/core'

export class GW_Crontab extends Model {
  static entity = 'gw_crontabs';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      minute: this.number(''),
      hour: this.number(''),
      day: this.number(''),
      month: this.number(''),
      dow: this.number(''),
      machine_label: this.string(''),
      label: this.string(''),
      enabled: this.boolean(''),
      args: this.string('').nullable(),
      kwargs: this.string('').nullable(),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
