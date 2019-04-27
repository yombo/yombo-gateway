import categories from '@/services/yboapiv1/categories';
import commands from '@/services/yboapiv1/commands';
import device_commands_inputs from '@/services/yboapiv1/device_commands_inputs';
import device_type_commands from '@/services/yboapiv1/device_type_commands';
import device_types from '@/services/yboapiv1/device_types';
import devices from '@/services/yboapiv1/devices';
import gateways from '@/services/yboapiv1/gateways';
import input_types from '@/services/yboapiv1/input_types';
import locations from '@/services/yboapiv1/locations';
import module_device_types from '@/services/yboapiv1/module_device_types';
import modules from '@/services/yboapiv1/modules';

export default {
    categories () {
        return categories
    },
    commands () {
        return commands
    },
    device_commands_inputs () {
        return device_commands_inputs
    },
    device_type_commands () {
        return device_type_commands
    },
    device_types () {
        return device_types
    },
    devices () {
        return devices
    },
    gateways () {
        return gateways
    },
    input_types () {
        return input_types
    },
    locations () {
        return locations
    },
    module_device_types () {
        return module_device_types
    },
    modules () {
        return modules
    },
}
