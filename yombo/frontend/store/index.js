/**
 * Performs the following tasks:
 * 1) Sets up Vuex ORM (https://github.com/vuex-orm/vuex-orm)
 * 2) Downloads core settings from the gateway to get started, and will be read by /plugins/index.js for processing.
 *    These are stores within the NUXT context, but are removed after being processed.
 *   1) Downloads the gateway's nuxt.env file.
 *   2) Downloads the gateway's system info.
 *   3) Downloads the user's access token to reach Yombo API.
 */

import VuexORM from '@vuex-orm/core'
import database from '@/database'

export const plugins = [
  VuexORM.install(database)
];

export const actions = {
  async nuxtClientInit({ commit }, context) {
    let response = await fetch('/nuxt.env', {
      credentials: 'include'
    });
    context.gateway_nuxt_env = await response.json();

    const protocol = ('https:' == document.location.protocol ? 'https://' : 'http://');
    const locationPart = ('local' == context.gateway_nuxt_env.client_location ? 'internal_' : 'external_');
    const portPart = ('https:' == document.location.protocol ? 'http_secure_port' : 'http_port');
    const portName = locationPart + portPart;
    let uriBase =  protocol + document.location.hostname + ":" + context.gateway_nuxt_env[portName];
    context.gateway_nuxt_env.http_uri = uriBase

    const fetch_headers = {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
    };
    response = await fetch(`${uriBase}/api/v1/system/info`, fetch_headers);
    context.gateway_system_info = await response.json();

    response = await fetch(`${uriBase}/api/v1/current_user/access_token`, fetch_headers);
    const access_token = await response.json();
    context.user_access_token = access_token['data']['attributes']
  }
}
