import createPersistedState from 'vuex-persistedstate'
import LZString from "lz-string";

export default ({store}) => {
  createPersistedState({
      key: 'ybo_fa_common1',
      paths:
        [
          'access_token', 'categories','commands', 'device_command_inputs', 'device_types', 'device_type_commands',
        ],
      storage: {
        getItem: key => LZString.decompressFromUTF16(localStorage.getItem(key)),
        setItem: (key, value) => localStorage.setItem(key, LZString.compressToUTF16(value)),
        removeItem: key => localStorage.removeItem(key),
        }
      }
  )(store);
  createPersistedState({
      key: 'ybo_fa_common2',
      paths:
        [
          'devices', 'gateways', 'input_types', 'locations', 'modules', 'module_device_types', 'systeminfo',
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
        setItem: (key, value) => localStorage.setItem(key, LZString.compressToUTF16(value)),
        removeItem: key => localStorage.removeItem(key),
        }
    })(store);
}
