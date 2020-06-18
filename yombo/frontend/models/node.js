import { Model } from '@vuex-orm/core'

export class Node extends Model {
  static entity = 'nodes';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static fields () {
    return {
      id: this.string(''),
      node_parent_id: this.string(''),
      gateway_id: this.string(''),
      node_type: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      always_load: this.boolean(''),
      destination: this.string(''),
      data: this.attr(''),
      data_content_type: this.string(''),
      status: this.number(''),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}

export class GW_Node extends Node {
  static entity = 'gw_nodes';
}

export class Yombo_Node extends Node {
  static entity = 'yombo_nodes';
}
