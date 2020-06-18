import { Model } from '@vuex-orm/core'

export class Gateway extends Model {
  static entity = 'gateways';

  static state()  {
    return {
      api_source: null,
    }
  }

  static additional_fields() {
    return {}
  }

  static fields() {
    return {
      id: this.string(''),
      machine_label: this.string(''),
      label: this.string(''),
      description: this.string('').nullable(),
      user_id: this.string(''),
      mqtt_auth: this.string('').nullable(),
      mqtt_auth_next: this.string('').nullable(),
      mqtt_auth_last_rotate_at: this.number(0).nullable(),
      internal_ipv4: this.string().nullable(),
      external_ipv4: this.string().nullable(),
      internal_ipv6: this.string().nullable(),
      external_ipv6: this.string().nullable(),
      internal_http_port: this.number().nullable(),
      external_http_port: this.number().nullable(),
      internal_http_secure_port: this.number().nullable(),
      external_http_secure_port: this.number().nullable(),
      internal_mqtt: this.number().nullable(),
      internal_mqtt_le: this.number().nullable(),
      internal_mqtt_ss: this.number().nullable(),
      internal_mqtt_ws: this.number().nullable(),
      internal_mqtt_ws_le: this.number().nullable(),
      internal_mqtt_ws_ss: this.number().nullable(),
      external_mqtt: this.number().nullable(),
      external_mqtt_le: this.number().nullable(),
      external_mqtt_ss: this.number().nullable(),
      external_mqtt_ws_le: this.number().nullable(),
      external_mqtt_ws_ss: this.number().nullable(),
      is_master: this.number().nullable(),
      master_gateway_id: this.string().nullable(),
      dns_name: this.string('').nullable(),
      last_connect_at: this.number(0),
      status: this.number(0),
      created_at: this.number(0),
      updated_at: this.number(0),
      ...this.additional_fields(),
    }
  }
}

export class GW_Gateway extends Gateway {
  static entity = 'gw_gateways';

    static additional_fields() {
    return {
      is_real: this.boolean(),
      com_status: this.string().nullable(),
      last_seen: this.string().nullable(),
      version: this.string().nullable(),
      ping_request_id: this.string().nullable(),
      ping_request_at: this.number().nullable(),
      ping_time_offset: this.number().nullable(),
      ping_roundtrip: this.number().nullable(),
    }
  }

}

export class Yombo_Gateway extends Gateway {
  static entity = 'yombo_gateways';
}
