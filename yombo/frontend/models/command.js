import { Base_Model } from '@/models/base_model'

class Command extends Base_Model {
  static entity = 'commands';

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      original_user_id: this.string(''),
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

export class GW_Command extends Command {
  static entity = 'gw_commands';
}

export class Yombo_Command extends Command {
  static entity = 'yombo_commands';
}
