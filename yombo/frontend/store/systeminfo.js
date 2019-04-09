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
});

export const actions = {
  async fetch( { commit }) {
    let response;

    try {
        response = await window.$nuxt.$gwapiv1.SystemInfo()
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
        return
    }
    // Handle success
    const data = response.data['data']['attributes']
    commit('SET_DATA', data)
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.label = data['label'];

    Object.keys(state).forEach(key => {
      let value = state[key];
      if(key in data){
        // console.log("key existss...")
        state[key] = data[key]
          // The property exists
      }else{
        // console.log("key NOOOO existss...")
          // The property DOESN'T exists
      }
      //use key and value here
    });
  }
};

