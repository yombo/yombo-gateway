import { Database } from '@vuex-orm/core'

import { GW_Atom, Yombo_Atom } from '@/models/atom'
import { GW_Category, Yombo_Category } from '@/models/category'
import { GW_Command, Yombo_Command}  from '@/models/command'
import { GW_Device, Yombo_Device } from '@/models/device'
import { GW_Device_Command_Input, Yombo_Device_Command_Input } from '@/models/device_command_input'
import { GW_Device_Type, Yombo_Device_Type } from '@/models/device_type'
import { GW_Device_Type_Command, Yombo_Device_Type_Command } from '@/models/device_type_command'
import { GW_Gateway, Yombo_Gateway } from '@/models/gateway'
import { GW_Input_Type, Yombo_Input_Type } from '@/models/input_type'
import { GW_Location, Yombo_Location } from '@/models/location'
import { GW_Module, Yombo_Module } from '@/models/module'
import { GW_Module_Device_Type, Yombo_Module_Device_Type } from '@/models/module_device_type'
import { GW_Node, Yombo_Node } from '@/models/node'
import { GW_User, Yombo_User } from '@/models/user'
import { GW_Variable_Data, Yombo_Variable_Data } from '@/models/variable_data'
import { GW_Variable_Field, Yombo_Variable_Field } from '@/models/variable_fields'
import { GW_Variable_Group, Yombo_Variable_Group } from '@/models/variable_groups'

// Gateway Only
import { GW_Authkey } from '@/models/authkey'
import { GW_Crontab } from '@/models/crontab'
import { GW_Config } from '@/models/config'
import { GW_Device_Command } from '@/models/device_command'
import { GW_Device_State } from '@/models/device_state'
import { GW_Discovery } from '@/models/discovery'
import { GW_Role } from '@/models/role'
import { GW_Scene } from '@/models/scene'
import { GW_State } from '@/models/state'

// Yombo API only
const database = new Database();

// Local items
import { Local_Presence } from '@/models/local_presence'

database.register(Local_Presence, {});

database.register(GW_Atom, {});
database.register(GW_Authkey, {});
database.register(GW_Category, {});
database.register(GW_Command, {});
database.register(GW_Config, {});
database.register(GW_Crontab, {});
database.register(GW_Device, {});
database.register(GW_Device_Command, {});
database.register(GW_Device_Command_Input, {});
database.register(GW_Device_State, {});
database.register(GW_Device_Type, {});
database.register(GW_Device_Type_Command, {});
database.register(GW_Discovery, {});
database.register(GW_Gateway, {});
database.register(GW_Input_Type, {});
database.register(GW_Location, {});
database.register(GW_Location, {});
database.register(GW_Module, {});
database.register(GW_Module_Device_Type, {});
database.register(GW_Node, {});
database.register(GW_Role, {});
database.register(GW_Scene, {});
database.register(GW_State, {});
database.register(GW_User, {});
database.register(GW_Variable_Data, {});
database.register(GW_Variable_Field, {});
database.register(GW_Variable_Group, {});

database.register(Yombo_Atom, {});
database.register(Yombo_Category, {});
database.register(Yombo_Command, {});
database.register(Yombo_Device, {});
database.register(Yombo_Device_Command_Input, {});
database.register(Yombo_Device_Type, {});
database.register(Yombo_Device_Type_Command, {});
database.register(Yombo_Gateway, {});
database.register(Yombo_Location, {});
database.register(Yombo_Input_Type, {});
database.register(Yombo_Module, {});
database.register(Yombo_Module_Device_Type, {});
database.register(Yombo_Node, {});
database.register(Yombo_User, {});
database.register(Yombo_Variable_Data, {});
database.register(Yombo_Variable_Field, {});
database.register(Yombo_Variable_Group, {});

export default database
