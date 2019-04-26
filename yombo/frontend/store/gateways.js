export const state = () => ({
  gateways: {},
  gateways_at: 0
});

export const actions = {
  fetch( { commit }) {
    let response;

    try {
        response = window.$nuxt.$yboapiv1.gateways().all()
        .then(response => {
          commit('SET_DATA', response.data['data'])
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.gateways = {}
    Object.keys(data).forEach(key => {
      state.gateways[data[key]['id']] = data[key]['attributes']
    });
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};
