import { Database } from '@vuex-orm/core'

import Category from '@/models/category'
import Command from '@/models/command'
import Device from '@/models/device'
import Device_Command_Input from '@/models/device_command_input'
import Device_Type from '@/models/device_type'
import Device_Type_Command from '@/models/device_type_command'
import Gateway from '@/models/gateway'
import Input_Type from '@/models/input_type'
import Location from '@/models/location'
import Module from '@/models/module'
import Module_Device_type from '@/models/module_device_type'

const database = new Database()

database.register(Category, {});
database.register(Command, {});
database.register(Device, {});
database.register(Device_Command_Input, {});
database.register(Device_Type, {});
database.register(Device_Type_Command, {});
database.register(Gateway, {});
database.register(Input_Type, {});
database.register(Location, {});
database.register(Module, {});
database.register(Device_Type_Command, {});
database.register(Module_Device_type, {});

export default database
