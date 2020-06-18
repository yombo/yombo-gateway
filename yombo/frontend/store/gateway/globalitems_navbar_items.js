export const state = () => ({
  data: {},
  last_download_at: 0,
  refresh_timeout: 3600,
});

export const actions = {
  fetch( { commit }) {
    let response;

    try {
      response = window.$nuxt.$gwapiv1.frontend().globalitems_navbar_items()
        .then(response => {
          commit('SET_DATA', response.data)
        });
    } catch (ex) {  // Handle error
      console.log(ex);
    }
  },
    // will only refresh if more than 1 hour has elapsed or the token expires within 2 hours.
    refresh( { state, dispatch }) {
    if (state.last_download_at <= Math.floor(Date.now()/1000) - state.refresh_timeout) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.data = data;
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};
