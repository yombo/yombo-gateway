import { Model } from '@vuex-orm/core'

export default class Module extends Model {
  static entity = 'modules';

  static fields () {
    return {
      id: this.string(''),
      user_id: this.string(''),
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
      doc_link: this.string(''),
      git_link: this.string(''),
      git_auto_approve: this.number(0),
      gateway_id: this.string(''),
      install_branch: this.string(''),
      require_approved: this.number(0),
      public: this.number(0),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }
}
