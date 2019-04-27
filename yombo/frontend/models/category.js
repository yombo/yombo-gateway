import { Model } from '@vuex-orm/core'

export default class Category extends Model {
  static entity = 'categories';

  static fields () {
    return {
      id: this.string(''),
      parent_id: this.string(''),
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
