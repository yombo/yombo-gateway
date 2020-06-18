import { Model } from '@vuex-orm/core'

export class Local_Presence extends Model {
  static entity = 'local_presence';

  static fields () {
    return {
      id: this.string(''),
      presence_type: this.string(''),
      presence_id: this.string(''),
      updated_at: this.number(0),
    }
  }
}
