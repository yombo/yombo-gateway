import { Model } from '@vuex-orm/core'

export default class Command extends Model {
  static entity = 'commands';

  static fields () {
    return {
      id: this.string(''),
      voice_cmd: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      public: this.number(0),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
