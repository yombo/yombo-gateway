"""
.. note::

  * End user documentation: `Scenes @ User Documentation <https://yombo.net/docs/gateway/web_interface/scenes>`_
  * For library documentation, see: `Scenes @ Library Documentation <https://yombo.net/docs/libraries/scenes>`_

Allows users to create scenes. The devices can be local devices or a device
on another gateway that is apart of the cluster.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import OrderedDict
from copy import deepcopy
import msgpack
import traceback
import types

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.lib.nodes import Node
from yombo.utils import (random_string, sleep, is_true_false, global_invoke_all, dict_filter, dict_merge,
                         bytes_to_unicode)

logger = get_logger("library.scenes")

REQUIRED_ACTION_KEYS = ['platform', 'webroutes', 'render_table_column_callback', 'scene_action_update_callback',
                        'add_url', 'note', 'handle_trigger_callback']
REQUIRED_ACTION_RENDER_TABLE_COLUMNS = ['action_type', 'attributes', 'edit_url', 'delete_url']

class Scenes(YomboLibrary, object):
    """
    Handles activities relating to scenes.
    """
    def __contains__(self, scene_requested):
        """
        Looks for a scene by it's ID or machine_label and returns true or false.

            >>> if '137ab129da9318' in self._Scenes:

        or:

            >>> if 'tv time' in self._Scenes:

        :raises YomboWarning: Raised when request is malformed.
        :param scene_requested: The scene ID or machine_label to search for.
        :type scene_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(scene_requested)
            return True
        except:
            return False

    def __getitem__(self, scene_requested):
        """
        Looks for a scene based on trigger ID or trigger machine_label and returns the scene.

        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._Scenes['137ab129da9318']  #by id

        or:

            >>> off_cmd = self._Scenes['bed_time']  #by label & machine_label

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param scene_requested: The scene ID or machine_label to search for.
        :type scene_requested: string
        :return: A pointer to the scene instance.
        :rtype: instance
        """
        return self.get(scene_requested)

    def __setitem__(self, scene_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, scene_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter scenes. """
        return self.scenes.__iter__()

    def __len__(self):
        """
        Returns an int of the number of scenes configured.

        :return: The number of scenes configured.
        :rtype: int
        """
        return len(self.scenes)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo scenes library"

    def keys(self):
        """
        Returns the keys (scene ID's) that are configured.

        :return: A list of scene IDs.
        :rtype: list
        """
        return list(self.scenes.keys())

    def items(self):
        """
        Gets a list of tuples representing the scenes configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.scenes.items())
    
    def _init_(self):
        """
        Defines library variables.

        :return:
        """
        self.scenes = {}  # store all scenes
        self.scenes_running = {}  # tracks if scene is running, stopping, or stopped
        self.scene_templates = {}  # hold any templates for scenes here for caching.
        self.scene_types_extra = {}  # any addition action types, fill by _scene_action_list_ hook.
        self.scene_types_urls = {
            "Device": {
                "add_url": "/scenes/{scene_id}/add_device",
                "note": "Control a device",
            },
            "Pause": {
                "add_url": "/scenes/{scene_id}/add_pause",
                "note": "Pause a scene",
            },
            "Scene": {
                "add_url": "/scenes/{scene_id}/add_scene",
                "note": "Control a scene",
            },
            "Template": {
                "add_url": "/scenes/{scene_id}/add_template",
                "note": " Advanced logic control",
            },
        }
        self.gateway_id = self._Configs.get2("core", "gwid", "local", False)

    def _load_(self, **kwargs):
        """
        Gets scene nodes.

        :return:
        """
        self.scenes = self._Nodes.search({'node_type': 'scene'})

        for scene_id, scene in self.scenes.items():
            if scene.status == 0:
                scene.status = 1
            if 'config' not in scene.data or isinstance(scene.data['config'], dict) is False:
                scene.data['config'] = {}
            if 'enabled' not in scene.data['config']:
                scene.data['config']['enabled'] = True
            if 'allow_intents' not in scene.data['config']:
                scene.data['config']['allow_intents'] = 1
            if 'description' not in scene.data['config']:
                scene.data['config']['description'] = scene.label
            self.scenes_running[scene_id] = 'stopped'
            self.patch_scene(scene)  # add methods an attributes to the node.
            actions = self.get_action_items(scene_id)
            for action_id, action in actions.items():
                if action['action_type'] == 'template':
                    self.scene_templates["%s_%s" % (scene_id, action_id)] = self._Template.new(action['template'])

    @inlineCallbacks
    def _start_(self, **kwargs):
        """
        Calls libraries and modules to check if any additional scene types should be defined.

        For an example, see the states library.

        **Hooks called**:

        * _scene_action_list_ : Expects a list of dictionaries containing additional scene types.

        **Usage**:

        .. code-block:: python

           def _scene_types_list_(self, **kwargs):
               '''
               Adds additional scene types.
               '''
               return [
                   {
                       "platform": "state",
                       "webroutes": "%syombo/lib/webinterface/routes/scenes/states.py" % self._Atoms.get('app_dir'),
                       "add_url": "/scenes/{scene_id}/add_state",
                       "note": "Change a state value",
                       "render_table_column_callback": self.scene_render_table_column,  # Show summary line in a table.
                       "scene_action_update_callback": self.scene_item_update,  # Return a dictionary to store as the item.
                       "handle_trigger_callback": self.scene_item_triggered,  # Do item activity
                   }
               ]

        """
        # Collect a list of automation source platforms.
        scene_types_extra = yield global_invoke_all('_scene_types_list_', called_by=self)
        logger.debug("scene_types_extra: {scene_types_extra}", scene_types_extra=scene_types_extra)
        for component_name, data in scene_types_extra.items():
            for scene_action in data:
                if not all(action_key in scene_action for action_key in REQUIRED_ACTION_KEYS):
                    logger.info("Scene platform doesn't have required fields, skipping: {required}",
                                required=REQUIRED_ACTION_KEYS)
                    continue
                action = dict_filter(scene_action, REQUIRED_ACTION_KEYS)
                action['platform_source'] = component_name
                self.scene_types_urls[action['platform']] = {
                    "add_url": action['add_url'],
                    "note": action['note'],
                }
                self.scene_types_extra[action['platform'].lower()] = action

    def scene_user_access(self, scene_id, access_type=None):
        """
        Gets all users that have access to this scene.

        :param access_type: If set to 'direct', then gets list of users that are specifically added to this device.
            if set to 'roles', returns access based on role membership.
        :return:
        """
        if access_type is None:
            access_type = 'direct'

        scene = self.get(scene_id)

        if access_type == 'direct':
            permissions = {}
            for email, user in self._Users.users.items():
                item_permissions = user.item_permissions
                if 'scene' in item_permissions and scene.machine_label in item_permissions['scene']:
                    if email not in permissions:
                        permissions[email] = []
                    for action in item_permissions['scene'][scene.machine_label]:
                        if action not in permissions[email]:
                            permissions[email].append(action)
            return permissions
        elif access_type == 'roles':
            return {}

    def scene_types_urls_sorted(self):
        """
        Return scene_type_urls, but sorted by display value.

        :param url_type:
        :return:
        """
        return OrderedDict(sorted(self.scene_types_urls.items(), key=lambda x: x))

    def get_scene_type_column_data(self, scene, action):
        """
        Called by the scenes macros.tpl file to get scene detail action for a custom scene type.

        :param scene:
        :param action:
        :return:
        """
        action_type = action['action_type']
        if action_type in self.scene_types_extra:
            return self.scene_types_extra[action_type]['render_table_column_callback'](scene, action)

    def get(self, requested_scene=None):
        """
        Return the requested scene, if it's found.

        :param requested_scene:
        :return:
        """
        if isinstance(requested_scene, Node):
            if requested_scene.node_type == 'scene':
                return requested_scene
            else:
                raise YomboWarning("Must submit a node type of scene if submitting an instance")

        if requested_scene is None:
            return OrderedDict(sorted(self.scenes.items(), key=lambda x: x[1].label))
        if requested_scene in self.scenes:
            return self.scenes[requested_scene]
        for temp_scene_id, scene in self.scenes.items():
            if scene.machine_label.lower() == requested_scene.lower():
                return scene
        raise KeyError("Cannot find requested scene : %s" % requested_scene)

    def get_action_items(self, scene_id, action_id=None):
        """
        Get a scene item.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        if action_id is None:
            return OrderedDict(sorted(scene.data['actions'].items(), key=lambda x: x[1]['weight']))
        else:
            try:
                return scene.data['actions'][action_id]
            except YomboWarning:
                raise KeyError("Unable to find requested action_id (%s) for scene_id (%s)." % (action_id, scene_id))

    def check_duplicate_scene(self, label=None, machine_label=None, scene_id=None):
        """
        Checks if a new/update scene label and machine_label are already in use.

        :param label:
        :param machine_label:
        :param scene_id: Ignore matches for a scene_id
        :return:
        """
        if label is None and machine_label is None:
            raise YomboWarning("Must have at least label or machine_label, or both.")
        for temp_scene_id, scene in self.scenes.items():
            if scene_id is not None and scene.node_id == scene_id:
                continue
            if scene.label.lower() == label.lower():
                raise YomboWarning("Scene with matching label already exists: %s" % scene.node_id)
            if scene.machine_label.lower() == machine_label.lower():
                raise YomboWarning("Scene with matching machine_label already exists: %s" % scene.node_id)

    def disable(self, scene_id, **kwargs):
        """
        Disable a scene. Just marks the configuration for the scene as disabled.

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        data = scene.data
        data['config']['enabled'] = False
        scene.on_change()
        self._Automation.trigger_monitor('scene',
                                         scene=scene,
                                         name=scene.machine_label,
                                         action='disable')

    def enable(self, scene_id, **kwargs):
        """
        Enable a scene. Just marks the configuration for the scene as enabled.

        :param scene_id:
        :return:
        """
        scene = self.scenes[scene_id]
        data = scene.data
        data['config']['enabled'] = True
        scene.on_change()
        self._Automation.trigger_monitor('scene',
                                         scene=scene,
                                         name=scene.machine_label,
                                         action='disable')

    def disable_intent(self, scene_id, **kwargs):
        """
        Disallow scene to be called via an intent.

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        data = scene.data
        data['config']['allow_intents'] = False
        scene.on_change()
        self._Automation.trigger_monitor('scene',
                                         scene=scene,
                                         name=scene.machine_label,
                                         action='disable_intent')

    def enable_intent(self, scene_id, **kwargs):
        """
        Allow scene to be called via an intent.

        :param scene_id:
        :return:
        """
        scene = self.scenes[scene_id]
        data = scene.data
        data['config']['allow_intents'] = True
        scene.on_change()
        self._Automation.trigger_monitor('scene',
                                         scene=scene,
                                         name=scene.machine_label,
                                         action='enable_intent')

    @inlineCallbacks
    def add(self, label, machine_label, description, status):
        """
        Add new scene.

        :param label:
        :param machine_label:
        :return:
        """
        self.check_duplicate_scene(label, machine_label)
        data = {
            'actions': {},
            'config': {
                'enabled': is_true_false(status),
                'description': description
            },
        }
        new_scene = yield self._Nodes.create(label=label,
                                             machine_label=machine_label,
                                             node_type='scene',
                                             data=data,
                                             data_content_type='json',
                                             gateway_id=self.gateway_id(),
                                             destination='gw',
                                             status=1)
        self.patch_scene(new_scene)
        self.scenes[new_scene.node_id] = new_scene
        reactor.callLater(0.001, global_invoke_all,
                                    '_scene_added_',
                                    called_by=self,
                                    scene_id=new_scene.node_id,
                                    scene=new_scene,
                          )
        return new_scene

    def edit(self, scene_id, label=None, machine_label=None, description=None, status=None, allow_intents=None):
        """
        Edit a scene label and machine_label.

        :param scene_id:
        :param label:
        :param machine_label:
        :param description:
        :param status:
        :return:
        """
        if label is not None and machine_label is not None:
            self.check_duplicate_scene(label, machine_label, scene_id)

        scene = self.get(scene_id)
        if label is not None:
            scene.label = label
        if machine_label is not None:
            scene.machine_label = machine_label
        if description is not None:
            scene.data['config']['description'] = description
        if status is not None:
            scene.status = is_true_false(status)
            scene.data['config']['enabled'] = scene.status
        if allow_intents is not None:
            scene.data['config']['allow_intents'] = allow_intents

        reactor.callLater(0.001, global_invoke_all,
                                 '_scene_edited_',
                                 called_by=self,
                                 scene_id=scene_id,
                                 scene=scene,
                          )
        return scene

    @inlineCallbacks
    def delete(self, scene_id, session=None):
        """
        Deletes the scene. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        data = scene.data
        data['config']['enabled'] = False
        results = yield self._Nodes.delete_node(scene.scene_id, session=session)
        yield global_invoke_all('_scene_deleted_',
                                called_by=self,
                                scene_id=scene_id,
                                scene=scene,
                                )
        return results

    @inlineCallbacks
    def duplicate_scene(self, scene_id):
        """
        Deletes the scene. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param scene_id:
        :return:
        """
        scene = self.get(scene_id)
        label = "%s (copy)" % scene.label
        machine_label = "%s_copy" % scene.machine_label
        if label is not None and machine_label is not None:
            self.check_duplicate_scene(label, machine_label, scene_id)
        new_data = bytes_to_unicode(msgpack.unpackb(msgpack.packb(scene.data)))  # had issues with deepcopy
        new_scene = yield self._Nodes.create(label=label,
                                             machine_label=machine_label,
                                             node_type='scene',
                                             data=new_data,
                                             data_content_type='json',
                                             gateway_id=self.gateway_id(),
                                             destination='gw',
                                             status=1)
        self.patch_scene(new_scene)
        self.scenes[new_scene.node_id] = new_scene
        yield global_invoke_all('_scene_added_',
                                called_by=self,
                                scene_id=scene_id,
                                scene=scene,
                                )
        return new_scene

    def balance_weights(self, scene_id):
        if scene_id not in self.scenes:
            return
        scene = self.get(scene_id)
        actions = deepcopy(scene.data['actions'])
        ordered_actions = OrderedDict(sorted(actions.items(), key=lambda x: x[1]['weight']))
        weight = 10
        for action_id, action in ordered_actions.items():
            self.scenes[scene_id].data['actions'][action_id]['weight'] = weight
            action['weight'] = weight
            weight += 10

    def add_action_item(self, scene_id, **kwargs):
        """
        Add new scene item.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        action_type = kwargs['action_type']
        if 'weight' not in kwargs:
            kwargs['weight'] = (len(scene.data['actions']) + 1) * 10

        action_id = random_string(length=15)
        if action_type == 'device':
            device = self._Devices[kwargs['device_machine_label']]
            command = self._Commands[kwargs['command_machine_label']]
            # This fancy inline just removes None and '' values.
            kwargs['inputs'] = {k: v for k, v in kwargs['inputs'].items() if v}

            scene.data['actions'][action_id] = {
                'action_id': action_id,
                'action_type': 'device',
                'device_machine_label': device.machine_label,
                'command_machine_label': command.machine_label,
                'inputs': kwargs['inputs'],
                'weight': kwargs['weight'],
            }

        elif action_type == 'pause':
            scene.data['actions'][action_id] = {
                'action_id': action_id,
                'action_type': 'pause',
                'duration': kwargs['duration'],
                'weight': kwargs['weight'],
            }

        elif action_type == 'scene':
            scene.data['actions'][action_id] = {
                'action_id': action_id,
                'action_type': 'scene',
                'scene_machine_label': kwargs['scene_machine_label'],
                'scene_action': kwargs['scene_action'],
                'weight': kwargs['weight'],
            }

        elif action_type == 'template':
            self.scene_templates["%s_%s" % (scene_id, action_id)] = self._Template.new(kwargs['template'])
            self.scene_templates["%s_%s" % (scene_id, action_id)].ensure_valid()
            scene.data['actions'][action_id] = {
                'action_id': action_id,
                'action_type': 'template',
                'description': kwargs['description'],
                'template': kwargs['template'],
                'weight': kwargs['weight'],
            }

        elif action_type in self.scene_types_extra:
            action_data = self.scene_types_extra[action_type]['scene_action_update_callback'](scene, kwargs)
            action_data['action_type'] = action_type
            action_data['action_id'] = action_id
            scene.data['actions'][action_id] = action_data

        else:
            raise KeyError("Invalid scene item type.")
        self.balance_weights(scene_id)
        scene.on_change()
        reactor.callLater(0.001, global_invoke_all,
                          '_scene_edited_',
                          called_by=self,
                          scene_id=scene_id,
                          scene=scene,
                          )
        return action_id

    def edit_action_item(self, scene_id, action_id, **kwargs):
        """
        Edit scene item.

        :param scene_id:
        :param action_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        action = self.get_action_items(scene_id, action_id)

        action_type = action['action_type']

        if action_type == 'device':
            device = self._Devices[kwargs['device_machine_label']]
            command = self._Commands[kwargs['command_machine_label']]
            action['device_machine_label'] = device.machine_label
            action['command_machine_label'] = command.machine_label
            kwargs['inputs'] = {k: v for k, v in kwargs['inputs'].items() if v}
            action['inputs'] = kwargs['inputs']
            action['weight'] = kwargs['weight']

        elif action_type == 'pause':
            action['duration'] = kwargs['duration']
            action['weight'] = kwargs['weight']

        elif action_type == 'scene':
            action['scene_machine_label'] = kwargs['scene_machine_label']
            action['scene_action'] = kwargs['scene_action']
            action['weight'] = kwargs['weight']

        elif action_type == 'template':
            self.scene_templates["%s_%s" % (scene_id, action_id)] = self._Template.new(kwargs['template'])
            self.scene_templates["%s_%s" % (scene_id, action_id)].ensure_valid()
            action['description'] = kwargs['description']
            action['template'] = kwargs['template']
            action['weight'] = kwargs['weight']

        elif action_type in self.scene_types_extra:
            action_data = self.scene_types_extra[action_type]['scene_action_update_callback'](scene, kwargs)
            action_data['action_type'] = action_type
            action_data['action_id'] = action_id
            scene.data['actions'][action_id] = action_data

        else:
            raise YomboWarning("Invalid scene item type.")
        self.balance_weights(scene_id)
        scene.on_change()
        reactor.callLater(0.001, global_invoke_all,
                          '_scene_edited_',
                          called_by=self,
                          scene_id=scene_id,
                          scene=scene,
                          )

    def delete_scene_item(self, scene_id, action_id):
        """
        Delete a scene action.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        action = self.get_action_items(scene_id, action_id)
        del scene.data['actions'][action_id]
        self.balance_weights(scene_id)
        reactor.callLater(0.001, global_invoke_all,
                          '_scene_edited_',
                          called_by=self,
                          scene_id=scene_id,
                          scene=scene,
                          )
        return scene

    def move_action_down(self, scene_id, action_id):
        """
        Move an action down.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        action = self.get_action_items(scene_id, action_id)
        action['weight'] += 11
        self.balance_weights(scene_id)
        reactor.callLater(0.001, global_invoke_all,
                          '_scene_edited_',
                          called_by=self,
                          scene_id=scene_id,
                          scene=scene,
                          )
        return scene

    def move_action_up(self, scene_id, action_id):
        """
        Move an action up.

        :param scene_id:
        :param action_id:
        :return:
        """
        scene = self.get(scene_id)
        action = self.get_action_items(scene_id, action_id)
        action['weight'] -= 11
        self.balance_weights(scene_id)
        reactor.callLater(0.001, global_invoke_all,
                          '_scene_edited_',
                          called_by=self,
                          scene_id=scene_id,
                          scene=scene,
                          )
        return scene

    def start(self, scene_id, **kwargs):
        """
        Trigger a scene to start.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        logger.debug("Scene '{label}' is starting.", label=scene.label)
        if scene.effective_status() != 1:
            logger.debug("Scene '{label}' is disabled, cannot start.", label=scene.label)
            raise YomboWarning("Scene is disabled.")
        if scene_id in self.scenes_running:
            if self.scenes_running[scene_id] in ("running", "stopping"):
                logger.debug("Scene '{label}' is already running, cannot start.", label=scene.label)
                return False  # already running
        self.scenes_running[scene_id] = "running"
        reactor.callLater(0.001, self.do_start, scene, **kwargs)
        return True

    @inlineCallbacks
    def do_start(self, scene, **kwargs):
        """
        Performs the actual trigger. It's wrapped here to handle any requested delays.

        :param scene:
        :param kwargs:
        :return:
        """
        logger.debug("Scene '{label}' is now running.", label=scene.label)
        scene_id = scene.scene_id
        scene = self.get(scene_id)
        actions = self.get_action_items(scene_id)
        self._Automation.trigger_monitor('scene',
                                         scene=scene,
                                         name=scene.machine_label,
                                         action='start')
        yield global_invoke_all('_scene_starting_',
                                called_by=self,
                                scene_id=scene_id,
                                scene=scene,
                                )

        logger.info("Scene is firing: {label}", label=scene.label)

        for action_id, action in actions.items():
            action_type = action['action_type']

            if action_type == "device":
                device = self._Devices[action['device_machine_label']]
                logger.info("Scene is firing {label}, device: {device}", label=scene.label, device=device.label)
                command = self._Commands[action['command_machine_label']]
                device.command(cmd=command,
                               auth_id=self._Users.system_user,
                               control_method='scene',
                               inputs=action['inputs'],
                               **kwargs)

            elif action_type == 'pause':
                final_duration = 0
                loops = 0
                duration = action['duration']
                if duration < 6:
                    final_duration = duration
                    loops = 1
                else:
                    loops = int(round(duration/5))
                    final_duration = duration / loops
                for current_loop in range(loops):
                    yield sleep(final_duration)
                    if self.scenes_running[scene_id] != "running":  # a way to kill this trigger
                        self.scenes_running[scene_id] = "stopped"
                        return False

            elif action_type == "scene":
                local_scene = self._Scenes.get(action['scene_machine_label'])
                scene_action = action['scene_action']
                if scene_action == 'enable':
                    self.enable(local_scene.scene_id)
                elif scene_action == 'disable':
                    self.disable(local_scene.scene_id)
                elif scene_action == 'start':
                    try:
                        self.start(local_scene.scene_id)
                    except Exception:  # Gobble everything up..
                        pass
                elif scene_action == 'stop':
                    try:
                        self.stop(local_scene.scene_id)
                    except Exception:  # Gobble everything up..
                        pass

            elif action_type == "template":
                try:
                    yield self.scene_templates["%s_%s" % (scene_id, action_id)].render(
                        {'current_scene': scene}
                    )
                except Exception as e:
                    logger.warn("-==(Warning: Scenes library had trouble with template==-")
                    logger.warn("Input template:")
                    logger.warn("{template}", template=action['template'])
                    logger.warn("---------------==(Traceback)==--------------------------")
                    logger.warn("{trace}", trace=traceback.format_exc())
                    logger.warn("--------------------------------------------------------")

                    logger.warn("Scene had trouble running template: {message}", message=e)

            elif action_type in self.scene_types_extra:
                action_data = self.scene_types_extra[action_type]['handle_trigger_callback'](scene, action)

            if self.scenes_running[scene_id] != "running":  # a way to kill this trigger
                self.scenes_running[scene_id] = "stopped"
                return False

        self.scenes_running[scene_id] = "stopped"

    def stop(self, scene_id, **kwargs):
        """
        Stop a currently running scene.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        if scene_id in self.scenes_running and self.scenes_running[scene_id] == "running":
            self.scenes_running[scene_id] = "stopping"
            results = True
        results = False
        reactor.callLater(0.001, global_invoke_all,
                                    '_scene_stopping_',
                                    called_by=self,
                                    scene_id=scene_id,
                                    scene=scene,
                          )

        self._Automation.trigger_monitor('scene',
                                         scene=scene,
                                         name=scene.machine_label,
                                         action='stop')
        return results

    def patch_scene(self, scene):
        """
        Adds additional attributes and methods to a node instance.

        :param scene:
        :return:
        """
        scene.scene_id = scene._node_id
        scene._Scene = self

        def add_action_item(node, **kwargs):
            results = node._Scene.add_action_item(node._node_id, **kwargs)
            return results

        @inlineCallbacks
        def delete(node, session):
            results = yield node._Scene.delete(node._node_id, session=session)
            return results

        def description(node):
            return node.data['config']['description']

        def disable(node, session):
            results = node._Scene.disable(node._node_id, session=session)
            return results

        def effective_status(node):
            if node.status == 2:
                return 2
            elif node.data['config']['enabled'] is True:
                return 1
            else:
                return 0

        def enabled(node):
            return node.data['config']['enabled']

        def enable(node, session):
            results = node._Scene.enable(node._node_id)
            return results

        def disable(node, session):
            results = node._Scene.disable(node._node_id)
            return results

        def start(node):
            results = node._Scene.start(node._node_id)
            return results

        def stop(node):
            results = node._Scene.stop(node._node_id)
            return results

        scene.add_action_item = types.MethodType(add_action_item, scene)
        scene.delete = types.MethodType(delete, scene)
        scene.description = types.MethodType(description, scene)
        scene.disable = types.MethodType(disable, scene)
        scene.effective_status = types.MethodType(effective_status, scene)
        scene.enabled = types.MethodType(enabled, scene)
        scene.enable = types.MethodType(enable, scene)
        scene.disable = types.MethodType(disable, scene)
        scene.start = types.MethodType(start, scene)
        scene.stop = types.MethodType(stop, scene)
