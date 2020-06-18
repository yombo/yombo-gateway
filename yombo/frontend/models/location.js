import { Model } from '@vuex-orm/core'

class Location extends Model {
  static entity = 'locations';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      location_type: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Location extends Location {
  static entity = 'gw_locations';
}

export class Yombo_Location extends Location {
  static entity = 'yombo_locations';
}
