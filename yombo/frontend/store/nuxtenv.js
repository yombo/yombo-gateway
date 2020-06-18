/**
 * from /nuxt.env API endpoint. Very basic information about the gateway and how
 * to access the gateway.
 */


export const state = () => ({
  gateway_id: null,
  working_dir: null,
  internal_http_port: 8080,
  external_http_port: 8080,
  internal_http_secure_port: 8443,
  external_http_secure_port: 8443,
  api_key: null,
  mqtt_port: null,
  mqtt_port_ssl: null,
  mqtt_port_websockets: null,
  mqtt_port_websockets_ssl: null,
  client_location: null,
  static_data: null,
  http_uri: null,
});

export const mutations = {
  set (state, values) {
    for (let property in values) {
      if (property in state) {
        state[property] = values[property];
      }
    }
    // Update http_uri
    const protocol = ('https:' == document.location.protocol ? 'https://' : 'http://');
    const locationPart = ('local' == state.client_location ? 'internal_' : 'external_');
    const portPart = ('https:' == document.location.protocol ? 'http_secure_port' : 'http_port');
    const portName = locationPart + portPart;
    state.http_uri = protocol + document.location.hostname + ":" + state[portName];
  },
};
