import { Model } from '@vuex-orm/core'

export class GW_Scene extends Model {
  static entity = 'gw_scenes';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      node_parent_id: this.string(null).nullable(),
      gateway_id: this.string(''),
      node_type: this.string(''),
      weight: this.number(''),
      machine_label: this.string(''),
      label: this.string(''),
      always_load: this.boolean(''),
      destination: this.string(''),
      data: this.attr({}),
      data_content_type: this.string(''),
      status: this.boolean(null),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
