import createPersistedState from 'vuex-persistedstate'
import LZString from "lz-string";

export default ({store}) => {
  createPersistedState({
      key: 'ybofa_yboapi',
      paths:
        [
          'yombo',
        ],
      storage: {
        getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
        setItem: (key, value) => localStorage.setItem(key, LZString.compressToUTF16(value)),
        removeItem: key => localStorage.removeItem(key),
        }
      }
  )(store);
  createPersistedState({
      key: 'ybofa_gwapi',
      paths:
        [
          'gateway',
        ],
      storage: {
        getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
        setItem: (key, value) => localStorage.setItem(key, LZString.compressToUTF16(value)),
        removeItem: key => localStorage.removeItem(key),
        }
      }
  )(store);
  createPersistedState({
    key: 'ybo_fa_orm',
    paths:
      [
        'entities'
      ],
    storage: {
        getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
        setItem: function (key, value) { localStorage.setItem(key, LZString.compressToUTF16(value)) },
        removeItem: key => localStorage.removeItem(key),
        }
    })(store);
  // createPersistedState({
  //   key: 'ybo_fa_modules',
  //   storage: {
  //       getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
  //       setItem: function (key, value) {
  //         if (key.startsWith('modules_')) {
  //           localStorage.setItem(key, LZString.compressToUTF16(value))
  //         }
  //       },
  //       removeItem: key => localStorage.removeItem(key),
  //       }
  //   })(store);
}
