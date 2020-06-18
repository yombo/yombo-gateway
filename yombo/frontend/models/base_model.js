import { Model } from '@vuex-orm/core'

export class Base_Model extends Model {
  static entity = 'atoms';

  static primaryKey = "id";

  static state () {
    return {
      api_source: null,
    }
  }
}
