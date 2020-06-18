import createPersistedState from 'vuex-persistedstate'
import LZString from "lz-string";
const debounce = require('lodash/debounce');

export default ({store}) => {
  createPersistedState({
      key: 'f_common',
      paths:
        [
          'frontend',
        ],
      setState: debounce((key, state, storage) => {
          storage.setItem(key, JSON.stringify(state));
          }, 500, { 'leading': false, 'trailing': true }
        ),
      storage: {
          getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
          setItem: function (key, value) {
            localStorage.setItem(key, LZString.compressToUTF16(value));
            },
          removeItem: key => localStorage.removeItem(key),
          }
      })(store);
  createPersistedState({
      key: 'f_gwapi',
      paths:
        [
          'gateway',
        ],
      setState: debounce((key, state, storage) => {
          storage.setItem(key, JSON.stringify(state));
          }, 4000, { 'leading': false, 'trailing': true }
        ),
      storage: {
          getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
          setItem: function (key, value) {
            localStorage.setItem(key, LZString.compressToUTF16(value));
            },
          removeItem: key => localStorage.removeItem(key),
          }
      })(store);
  createPersistedState({
      key: 'f_orm',
      paths:
        [
          'entities'
        ],
      setState: debounce((key, state, storage) => {
          let new_state = {entities: {}};

          for (let [key, value] of Object.entries(state['entities'])) {
            if (key.startsWith("local_")) {
              continue;
            }
            if (key.startsWith("$")) {
              new_state['entities'][key] = value;
              continue;
            }
            if (value.api_source !== undefined) {
              if (value.api_source == "gw") {
                new_state['entities'][key] = value;
              }
            }
          }
          storage.setItem(key, JSON.stringify(new_state));
          }, 4500, { 'leading': false, 'trailing': true }
        ),
      storage: {
          getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
          setItem: function (key, value) {
            localStorage.setItem(key, LZString.compressToUTF16(value));
            },
          removeItem: key => localStorage.removeItem(key),
          }
      })(store);
  createPersistedState({
      key: 'f_yboapi',
      paths:
        [
          'yombo',
        ],
      setState: debounce((key, state, storage) => {
          storage.setItem(key, JSON.stringify(state));
          }, 5000, { 'leading': false, 'trailing': true }
        ),
      storage: {
          getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
          setItem: function (key, value) {
            localStorage.setItem(key, LZString.compressToUTF16(value));
            },
          removeItem: key => localStorage.removeItem(key),
          }
      })(store);
}
