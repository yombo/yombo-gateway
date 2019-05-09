async function a_fetch(settings, commit) {
  await settings.api_all()
    .then(function (response) {
      commit('SET_DATA', response.data['data']);
      return true;
    })
    .catch(function (error) {
      console.log(error);
    });
}

async function a_fetchOne(settings, commit, payload) {
  await settings.api.fetchOne(payload)
    .then(function (response) {
      commit('UPDATE', response.data['data']['attributes']);
      return true;
    })
    .catch(function (error) {
      console.log(error);
    });
}

function a_refresh(settings, state, dispatch) {
  // console.log(state)
  // console.log("a refresh last:" + state.last_download_at)
  // console.log("a refresh curr:" + Math.floor(Date.now() - (120*1000)))
  var refresh_age = 120
  if('refresh_age' in settings) {
    refresh_age = settings.refresh_age
  }
  if (state.last_download_at <= Math.floor(Date.now() - (refresh_age*1000))) {
    dispatch('fetch');
  }
}

async function a_update(settings, commit, state, dispatch, payload) {
  var id = payload.id;
  delete payload.id;
  await settings.api.patch(id, payload)
    .then(function (response) {
      // console.log(response);
      commit('UPDATE', response.data['data']['attributes']);
      return response.data['data']['attributes']['status']
    })
    .catch(function (error) {
      console.log(error);
    });
}

async function a_enable(settings, commit, state, dispatch, payload) {
  await settings.api.patch(payload, {status: 1})
    .then(function (response) {
      // console.log("enable results:");
      // console.log(response);
      commit('UPDATE', response.data['data']['attributes']);
      return response.data['data']['attributes']['status']
    })
    .catch(function (error) {
      console.log(error);
    });
}

async function a_delete_with_status(settings, commit, state, dispatch, payload) {
    await settings.api.patch(payload, {status: 0})
      .then(function (response) {
        // console.log("delete status results:");
        // console.log(response);
        commit('UPDATE', response.data['data']['attributes']);
        return response.data['data']['attributes']['status']
      })
      .catch(function (error) {
        console.log(error);
      });
}

async function a_delete(settings, commit, state, dispatch, payload) {
    await settings.api.delete(payload)
      .then(function (response) {
        // console.log(response);
        // commit('DELETE', response.data['data']['attributes']);
        return response.data['data']['attributes']
      })
      .catch(function (error) {
        console.log(error);
      });
}

async function a_disable(settings, commit, state, dispatch, payload) {
    await settings.api.patch(payload, {status: 0})
      .then(function (response) {
        // console.log("disable results:");
        // console.log(response);
        commit('UPDATE', response.data['data']['attributes']);
        return response.data['data']['attributes']['status']
      })
      .catch(function (error) {
        console.log(error);
      });
}

export {
  a_fetch,
  a_fetchOne,
  a_refresh,
  a_update,
  a_enable,
  a_delete,
  a_delete_with_status,
  a_disable,
}
