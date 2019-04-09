// ~/plugins/localStorage.js

import createPersistedState from 'vuex-persistedstate'

export default ({store}) => {
  createPersistedState({
      key: 'ybofront',
      // getState: (key) => localStorage.getItem(key),
      // setState: (key, state) => localStorage.setItem(key, state)
  })(store)
}
