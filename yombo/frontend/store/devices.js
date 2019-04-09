export const state = () => ({
  devices: {}
});


export const actions = {
  async fetch( { commit }) {
    let response;

    try {
      console.log("about to get devices....");
        response = await window.$nuxt.$yboapiv1.Devices()
    } catch (ex) {  // Handle error
      console.log("storage/devices: has an error 2");
      console.log(response);
      console.log(ex);
        return
    }
    console.log(response.data);
    return
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

