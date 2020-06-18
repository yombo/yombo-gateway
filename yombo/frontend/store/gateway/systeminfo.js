export const state = () => ({
  gateway_id: null,
  dns_name: null,
  is_master: null,
  master_gateway_id: null,
  label: 'Unknown',
  description: '',
  internal_ipv4: null,
  external_ipv4: null,
  internal_http_port: null,
  external_http_port: null,
  external_http_secure_port: null,
  internal_mqtt: null,
  internal_mqtt_le: null,
  internal_mqtt_ws: null,
  external_mqtt: null,
  external_mqtt_le: null,
  version: null,
  operating_mode: null,
  running_since: null,
  last_download_at: 0,
  refresh_timeout: 300,
});

export const actions = {
  fetch( { commit }) {
    let response;

    try {
      response = window.$nuxt.$gwapiv1.system().info()
        .then(response => {
          commit('SET_DATA', response.data['data']['attributes']);
          commit('touch_downloaded');
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
    refresh( { state, dispatch }) {
    if (state.last_download_at === null || state.last_download_at <= Math.floor(Date.now() - (state.refresh_timeout*1000))) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    // state.label = data['label'];
    Object.keys(state).forEach(key => {
      state[key] = data[key];
    });
    state.last_download_at = Math.floor(Date.now() / 1000);
  },
  touch_downloaded(state) {
    state.last_download_at = Number(Date.now());
  }
};

export const getters = {
  gateway_id: state => () => {
    return state.gateway_id;
  },
};
