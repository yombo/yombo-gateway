export const state = () => ({
  access_token: null,
  access_token_expires: null,
  session: null,
  last_download_at: 0,
  refresh_timeout: 3600,
});

import Vue from 'vue'
import YomboApiV1 from '@/services/yboapiv1/YomboApiV1'

export const actions = {
  async fetch( { commit } ) {
    // let response;

    try {
      await window.$nuxt.$gwapiv1.current_user().access_token()
        .then(function (response) {
          commit('SET_DATA', response.data['data']['attributes'])
          Object.defineProperty(Vue.prototype, '$yboapiv1axios', { value: GetYomboV1Client(response.data['data']['attributes']['access_token']), writable: true });
        });
    } catch (ex) {  // Handle error
      return
    }
  },
    // will only refresh if more than 1 hour has elapsed or the token expires within 2 hours.
    async refresh( { state, dispatch }) {
    if (state.last_download_at <= Math.floor(Date.now()/1000) - state.refresh_timeout
        || state.access_token_expires <= Math.floor(Date.now()/1000) + state.refresh_timeout * 2) {
      await dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, values) {
    state.access_token = values.access_token;
    state.access_token_expires = values.access_token_expires;
    state.session = values.session;
    state.last_download_at = Math.floor(Date.now() / 1000);
    if ("$nuxt" in window && "$bus" in window.$nuxt) {
      window.$nuxt.$bus.$emit('user_access_token', 'received');
    }
  }
};

export const getters = {
  token: state => () => {
    return state.access_token;
  },
  expires: state => () => {
    return state.access_token_expires;
  }
};
