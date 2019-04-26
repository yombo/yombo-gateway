export const state = () => ({
  locations: {},
  last_download_at: 0
});

export const actions = {
  fetch( { commit }) {
    let response;
    try {
      response = window.$nuxt.$yboapiv1.locations().all()
        .then(response => {
          commit('SET_DATA', response.data['data'])
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
  refresh( { state, dispatch }) {
    // this.$bus.$emit('messageSent', 'over there');
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 60) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.locations = {}
    Object.keys(data).forEach(key => {
      state.locations[data[key]['id']] = data[key]['attributes']
    });
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};
