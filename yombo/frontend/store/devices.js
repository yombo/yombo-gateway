import Device from '@/models/device'

export const state = () => ({
  last_download_at: 0
});

export const actions = {
  fetch( { commit, dispatch }) {
    let response;
    try {
      response = window.$nuxt.$yboapiv1.devices().allGW()
        .then(response => {
          commit('SET_DATA', response.data['data']);
          dispatch('locations/refresh', {}, {root:true});
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
  refresh( { state, dispatch }) {
      // this.$bus.$emit('messageSent', 'over there');
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 120) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, payload) {
    Device.deleteAll();
    Object.keys(payload).forEach(key => {
      // console.log("adding device:");
      // console.log(payload[key]['attributes']);
      Device.insert({
        data: payload[key]['attributes'],
      })
    });
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};
