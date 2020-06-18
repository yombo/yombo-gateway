import { Model } from '@vuex-orm/core'

export class User extends Model {
  static entity = 'users';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      gateway_id: this.string(''),
      email: this.string(''),
      name: this.string(null),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_User extends User {
  static entity = 'gw_users';
}

export class Yombo_User extends User {
  static entity = 'yombo_users';
}
