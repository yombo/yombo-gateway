import { Model } from '@vuex-orm/core'

export class Module extends Model {
  static entity = 'gateway_modules';

  static state ()  {
    return {
      api_source: null,
    }
  }

  static additional_fields() {
    return {}
  }

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
      original_user_id: this.string(''),
      module_type: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      short_description: this.string(''),
      medium_description: this.string(''),
      description: this.string(''),
      medium_description_html: this.string(''),
      description_html: this.string(''),
      see_also: this.string('').nullable(),
      repository_link: this.string(''),
      issue_tracker_link: this.string('').nullable(),
      install_count: this.number(0),
      doc_link: this.string(''),
      git_link: this.string(''),
      git_auto_approve: this.number(0),
      public: this.number(0),
      status: this.number(0),
      install_branch: this.string(''),
      created_at: this.number(0),
      updated_at: this.number(0),
      ...this.additional_fields(),
    }
  }
}


export class GW_Module extends Module {
  static entity = 'gw_gateway_modules';

  static additional_fields() {
    return {
      require_approved: this.boolean(''),
      load_source: this.string(''),
    }
  }

}

export class Yombo_Module extends Module {
  static entity = 'yombo_gateway_modules';
}
