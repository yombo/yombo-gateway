export const state = () => ({
  access_token: "",
  access_token_expires: "",
  last_download_at: 0
});

export const actions = {
  fetch( { commit }) {
    let response;

    try {
      response = window.$nuxt.$gwapiv1.user().access_token()
        .then(response => {
          commit('SET_DATA', response.data['data']['attributes'])
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
    // will only refresh if more than 1 hour has elapsed or the token expires within 2 hours.
    refresh( { state, dispatch }) {
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 3600
        || state.access_token_expires <= Math.floor(Date.now()/1000) + 7200) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    this.$bus.$emit('user_access_token', 'received');
    state.access_token = data['access_token'];
    state.access_token_expires = data['access_token_expires'];
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};

