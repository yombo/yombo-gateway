import { Model } from '@vuex-orm/core'

export class Category extends Model {
  static entity = 'gw_categories';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      category_parent_id: this.string(''),
      category_type: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Category extends Category {
  static entity = 'gw_categories';
}

export class Yombo_Category extends Category {
  static entity = 'yombo_categories';
}
