// This gets all commands available for a device.
// Not to be confused with device commands: list of commands sent to devices.
import gwapiv1 from '@/services/gwapiv1'

export default {
    commands() {
        return gwapiv1().get('devices/commands');
    },
    device_states() {
        return gwapiv1().get('devices/states');
    },
}
