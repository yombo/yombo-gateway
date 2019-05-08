import createPersistedState from 'vuex-persistedstate'
// import createPersistedState from './persistdata'
import LZString from "lz-string";
const debounce = require('lodash/debounce');

export default ({store}) => {
  createPersistedState({
      key: 'ybofa_yboapi',
      paths:
        [
          'yombo',
        ],
      setState: debounce((key, state, storage) => {
          storage.setItem(key, JSON.stringify(state));
          }, 2000, { 'leading': false, 'trailing': true }
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
      key: 'ybofa_gwapi',
      paths:
        [
          'gateway',
        ],
      setState: debounce((key, state, storage) => {
          storage.setItem(key, JSON.stringify(state));
          }, 2000, { 'leading': false, 'trailing': true }
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
      key: 'ybo_fa_orm',
      paths:
        [
          'entities'
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
      key: 'ybo_fa_modules',
      paths:
        [
          'modules'
        ],
      setState: debounce((key, state, storage) => {
          storage.setItem(key, JSON.stringify(state));
          }, 2000, { 'leading': false, 'trailing': true }
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
