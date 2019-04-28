import humanizeDuration from 'humanize-duration';

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
  fetchOne( { commit, dispatch }, payload) {
    let response;
    console.log("fetchone payload:" + payload)
    try {
      response = window.$nuxt.$yboapiv1.devices().find(payload)
        .then(response => {
          commit('UPDATE', response.data['data']['attributes']);
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
  refresh({ state, dispatch }) {
      // this.$bus.$emit('messageSent', 'over there');
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 120) {
      dispatch('fetch');
    }
  },
  update({ commit, state, dispatch }, payload) {
    let id = payload.id;
    delete payload.id;
    window.$nuxt.$yboapiv1.devices().patch(payload.id, payload)
      .then(function (response) {
        console.log(response);
        dispatch('devices/fetchOne', id, {root:true});
      })
      .catch(function (error) {
        console.log(error);
      });
  },
  async delete({ commit, state, dispatch }, payload) {
    await window.$nuxt.$yboapiv1.devices().patch(payload)
      .then(function (response) {
        commit('UPDATE', response.data['data']['attributes']);
        return response.data['data']['attributes']['status']
      })
      .catch(function (error) {
        console.log(error);
      });
  },
  async enable({ commit, state, dispatch }, payload) {
    await window.$nuxt.$yboapiv1.devices().patch(payload, {status: 1})
      .then(function (response) {
        console.log(response);
        commit('UPDATE', response.data['data']['attributes']);
        return response.data['data']['attributes']['status']
      })
      .catch(function (error) {
        console.log(error);
      });
  },
  async disable({ commit, state, dispatch }, payload) {
    await window.$nuxt.$yboapiv1.devices().patch(payload, {status: 0})
      .then(function (response) {
        console.log(response);
        commit('UPDATE', response.data['data']['attributes']);
        return response.data['data']['attributes']['status']
      })
      .catch(function (error) {
        console.log(error);
      });
  },
};

export const mutations = {
  SET_DATA(state, payload) { // Clears all previous data and loads it.
    Device.deleteAll();
    Object.keys(payload).forEach(key => {
      Device.insert({
        data: payload[key]['attributes'],
      });
    });
    state.last_download_at = Number(Date.now());
    this.$bus.$emit('store_devices_updates', state.last_download_at);
    // console.log("dvice at: " + state.last_download_at);
  },
  UPDATE(state, payload) { // Clears all previous data and loads it.
    console.log("Update, got payload:");
    console.log(payload);
    Device.insert({
      data: payload,
    });
  },
};

export const getters = {
  data_age: state => () => {
    return Date.now() - state.last_download_at;
  },
  display_age: (state, getters) => (locale) => {
    return humanizeDuration(getters['data_age'](), { language: locale, round: true });
  }
};
