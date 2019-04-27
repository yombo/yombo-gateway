import { Model } from '@vuex-orm/core'

export default class Gateway extends Model {
  static entity = 'gateways';

  static fields () {
    return {
      id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string(''),
      mqtt_auth: this.string(''),
      mqtt_auth_next: this.string(''),
      mqtt_auth_last_rotate_at: this.number(0),
      internal_http_port: this.number(0),
      external_http_port: this.number(0),
      internal_http_secure_port: this.number(0),
      external_http_secure_port: this.number(0),
      internal_mqtt: this.number(0),
      internal_mqtt_le: this.number(0),
      internal_mqtt_ss: this.number(0),
      internal_mqtt_ws: this.number(0),
      internal_mqtt_ws_le: this.number(0),
      internal_mqtt_ws_ss: this.number(0),
      external_mqtt: this.number(0),
      external_mqtt_le: this.number(0),
      external_mqtt_ss: this.number(0),
      external_mqtt_ws_le: this.number(0),
      external_mqtt_ws_ss: this.number(0),
      is_master: this.number(0),
      master_gateway_id: this.string('').nullable(),
      dns_name: this.string('').nullable(),
      last_connect_at: this.number(0),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
    }
  }

}
