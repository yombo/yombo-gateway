"""
Allows users to create scenes. The devices can be local devices or a device
on another gateway that is apart of the cluster.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.17.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import OrderedDict
import copy
import types

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import random_string, sleep, is_true_false

logger = get_logger("library.scenes")


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
        self.scenes = {}
        self.scenes_running = {}
        self.scene_templates = {}
        self.gateway_id = self._Configs.get2("core", "gwid", "local", False)

    def _load_(self, **kwargs):
        """
        Gets scene nodes.

        :return:
        """
        self.scenes = self._Nodes.search({'node_type': 'scene'})
        # Some scenes don't have this. This check will be removed later.
        for scene_id, scene in self.scenes.items():
            if scene.status == 0:
                scene.status = 1
            if 'config' not in scene.data or isinstance(scene.data['config'], dict) is False:
                scene.data['config'] = {}
            if 'enabled' not in scene.data['config']:
                print("data: %s" % scene.data)
                scene.data['config']['enabled'] = True
            if 'description' not in scene.data['config']:
                scene.data['config']['description'] = scene.label
            self.scenes_running[scene_id] = 'stopped'
            self.patch_scene(scene)  # add methods an attributes to the node.
            items = self.get_item(scene_id)
            for item_id, item in items.items():
                if item['item_type'] == 'template':
                    self.scene_templates["%s_%s" % (scene_id, item_id)] = self._Template.new(item['template'])

    def get(self, requested_scene=None):
        """
        Return the requested scene, if it's found.

        :param requested_scene:
        :return:
        """
        if requested_scene is None:
            return OrderedDict(sorted(self.scenes.items(), key=lambda x: x[1].label))
        if requested_scene in self.scenes:
            return self.scenes[requested_scene]
        for temp_scene_id, scene in self.scenes.items():
            if scene.machine_label.lower() == requested_scene.lower():
                return scene
        raise YomboWarning("Cannot find requested scene : %s" % requested_scene)

    def get_scene_item(self, scene_id, item_id=None):
        """
        Get a scene item.

        :param scene_id:
        :param item_id:
        :return:
        """
        scene = self.get(scene_id)
        if item_id is None:
            return scene, OrderedDict(sorted(scene.data['items'].items(), key=lambda x: x[1]['weight']))
        else:
            try:
                return scene, scene.data['items'][item_id]
            except YomboWarning:
                raise YomboWarning("Unable to find requested item for the provide scene_id.")


    def get_item(self, scene_id, item_id=None):
        """
        Get a scene item.

        :param scene_id:
        :param item_id:
        :return:
        """
        scene = self.get(scene_id)
        if item_id is None:
            return OrderedDict(sorted(scene.data['items'].items(), key=lambda x: x[1]['weight']))
        else:
            try:
                return scene.data['items'][item_id]
            except YomboWarning:
                raise YomboWarning("Unable to find requested item for the provide scene_id.")

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
        Disable a scene. Just marks the configuration item as disabled.

        :param scene_id:
        :return:
        """
        scene = self.scenes.get(scene_id)
        data = scene.data
        data['config']['enabled'] = False
        scene.on_change()

    def enable(self, scene_id, **kwargs):
        """
        Enable a scene. Just marks the configuration item as enabled.

        :param scene_id:
        :return:
        """
        print("starting enable. 1")
        scene = self.scenes[scene_id]
        print("starting enable. 2")
        data = scene.data
        print("starting enable. 3")
        data['config']['enabled'] = True
        print("starting enable. 5")
        scene.on_change()

    @inlineCallbacks
    def add(self, label, machine_label, description, status):
        """
        Add new scene.

        :param label:
        :param machine_label:
        :return:
        """
        # Example data structure
        #
        # data = {
        #     'items': {
        #         '123-itemid': {
        #             'weight': 0,
        #             'type': 'state',
        #             'name': 'some_state',
        #             'value': 'new_value',
        #             'value_type': 'string',  # or int, bool
        #         },
        #         '987-itemid': {
        #             'weight': 1,
        #             'type': 'device',
        #             'device_id': 'abc-deviceid',
        #             'command': 'on',
        #             'inputs': {
        #                 'percent': 50,
        #                 ],
        #             },
        #         },
        #     },
        #     'config': {
        #         'enabled': 1,  # enabled
        #     },
        # }
        self.check_duplicate_scene(label, machine_label)
        data = {
            'items': {},
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
        return new_scene

    def edit(self, scene_id, label=None, machine_label=None, description=None, status=None):
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
        return scene

    @inlineCallbacks
    def delete(self, scene_id, session=None):
        """
        Deletes the scene. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param scene_id:
        :return:
        """
        scene = self.scenes.get(scene_id)
        data = scene.data
        data['config']['enabled'] = False
        results = yield self._Nodes.delete_node(scene.scene_id, session=session)
        return results

    @inlineCallbacks
    def duplicate_scene(self, scene_id):
        """
        Deletes the scene. Will disappear on next restart. This allows the user to recover it.
        This marks the node to be deleted!

        :param scene_id:
        :return:
        """
        scene = self.scenes.get(scene_id)
        label = "%s (copy)" % scene.label
        machine_label = "%s_copy" % scene.machine_label
        if label is not None and machine_label is not None:
            self.check_duplicate_scene(label, machine_label, scene_id)
        new_scene = yield self._Nodes.create(label=label,
                                             machine_label=machine_label,
                                             node_type='scene',
                                             data=scene.data,
                                             data_content_type='json',
                                             gateway_id=self.gateway_id(),
                                             destination='gw',
                                             status=1)
        self.patch_scene(new_scene)
        self.scenes[new_scene.node_id] = new_scene
        return new_scene

    def balance_weights(self, scene_id):
        if scene_id not in self.scenes:
            return
        scene = self.get(scene_id)
        items = copy.deepcopy(scene.data['items'])
        o_items = OrderedDict(sorted(items.items(), key=lambda x: x[1]['weight']))
        weight = 10
        for item_id, item in o_items.items():
            item['weight'] = weight
            weight += 10
        scene.data['items'] = o_items

    def add_scene_item(self, scene_id, **kwargs):
        """
        Add new scene item.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.get(scene_id)
        item_type = kwargs['item_type']
        if 'order' not in kwargs:
            kwargs['order'] = len(scene.data['items'])

        item_id = random_string(length=15)
        if item_type == 'device':
            device = self._Devices[kwargs['device_id']]
            command = self._Commands[kwargs['command_id']]
            # This fancy inline just removes None and '' values.
            kwargs['inputs'] = {k: v for k, v in kwargs['inputs'].items() if v}

            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'device',
                'device_id': device.device_id,
                'command_id': command.command_id,
                'inputs': kwargs['inputs'],
                'weight': kwargs['weight'],
            }

        elif item_type == 'pause':
            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'pause',
                'duration': kwargs['duration'],
                'weight': kwargs['weight'],
            }

        elif item_type == 'scene':
            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'scene',
                'machine_label': kwargs['machine_label'],
                'action': kwargs['action'],
                'weight': kwargs['weight'],
            }

        elif item_type == 'state':
            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'state',
                'name': kwargs['name'],
                'value': kwargs['value'],
                'value_type': kwargs['value_type'],
                'weight': kwargs['weight'],
            }

        elif item_type == 'template':
            self.scene_templates["%s_%s" % (scene_id, item_id)] = self._Template.new(kwargs['template'])
            self.scene_templates["%s_%s" % (scene_id, item_id)].ensure_valid()
            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'template',
                'description': kwargs['description'],
                'template': kwargs['template'],
                'weight': kwargs['weight'],
            }

        else:
            raise YomboWarning("Invalid scene item type.")
        self.balance_weights(scene_id)
        scene.on_change()
        return item_id

    def edit_scene_item(self, scene_id, item_id, **kwargs):
        """
        Edit scene item.

        :param scene_id:
        :param item_id:
        :param kwargs:
        :return:
        """
        scene, item = self.get_scene_item(scene_id, item_id)

        item_type = item['item_type']

        if item_type == 'device':
            device = self._Devices[kwargs['device_id']]
            command = self._Commands[kwargs['command_id']]
            item['device_id'] = device.device_id
            item['command_id'] = command.command_id
            kwargs['inputs'] = {k: v for k, v in kwargs['inputs'].items() if v}
            item['inputs'] = kwargs['inputs']
            item['weight'] = kwargs['weight']

        elif item_type == 'pause':
            item['duration'] = kwargs['duration']
            item['weight'] = kwargs['weight']

        elif item_type == 'scene':
            item['machine_label'] = kwargs['machine_label']
            item['action'] = kwargs['action']
            item['weight'] = kwargs['weight']

        elif item_type == 'state':
            item['name'] = kwargs['name']
            item['value'] = kwargs['value']
            item['value_type'] = kwargs['value_type']
            item['weight'] = kwargs['weight']

        elif item_type == 'template':
            self.scene_templates["%s_%s" % (scene_id, item_id)] = self._Template.new(kwargs['template'])
            self.scene_templates["%s_%s" % (scene_id, item_id)].ensure_valid()
            item['description'] = kwargs['description']
            item['template'] = kwargs['template']
            item['weight'] = kwargs['weight']
            self.scene_templates["%s_%s" % (scene_id, item_id)] = self._Template.new(kwargs['template'])

        else:
            raise YomboWarning("Invalid scene item type.")
        self.balance_weights(scene_id)
        scene.on_change()

    def delete_scene_item(self, scene_id, item_id):
        """
        Delete a scene item.

        :param scene_id:
        :param item_id:
        :return:
        """
        scene, item = self.get_scene_item(scene_id, item_id)
        del scene.data['items'][item_id]
        self.balance_weights(scene_id)
        return scene

    def move_item_down(self, scene_id, item_id):
        """
        Move an item down.

        :param scene_id:
        :param item_id:
        :return:
        """
        scene, item = self.get_scene_item(scene_id, item_id)
        item['weight'] += 11
        self.balance_weights(scene_id)
        return scene

    def move_item_up(self, scene_id, item_id):
        """
        Move an item up.

        :param scene_id:
        :param item_id:
        :return:
        """
        scene, item = self.get_scene_item(scene_id, item_id)
        item['weight'] -= 11
        self.balance_weights(scene_id)
        return scene

    def trigger(self, scene_id, **kwargs):
        """
        Trigger a scene to start.

        :param scene_id:
        :param kwargs:
        :return:
        """
        print("starting trigger. 1")
        scene = self.scenes.get(scene_id)
        if scene.effective_status() != 1:
            raise YomboWarning("Scene is disabled.")
        if scene_id in self.scenes_running:
            if self.scenes_running[scene_id] in ("running", "stopping"):
                return False  # already running
        self.scenes_running[scene_id] = "running"
        print("starting trigger. 3.. %s" % scene)
        reactor.callLater(0.001, self.do_trigger, scene, **kwargs)
        print("starting trigger. 4")
        return True

    @inlineCallbacks
    def do_trigger(self, scene, **kwargs):
        """
        Performs the actual trigger. It's wrapped here to handle any requested delays.

        :param scene:
        :param kwargs:
        :return:
        """
        print("starting do_trigger. 1")
        scene_id = scene.scene_id
        items = self.get_item(scene_id)

        for item_id, item in items.items():
            if item['item_type'] == "device":
                device = self._Devices[item['device_id']]
                command = self._Commands[item['command_id']]
                device.command(cmd=command,
                               requested_by={'user_id': "System", "component": "yombo.lib.scenes"},
                               control_method='scene',
                               inputs=item['inputs'],
                               **kwargs)

            elif item['item_type'] == 'pause':
                final_duration = 0
                loops = 0
                duration = item['duration']
                if duration < 10:
                    final_duration = duration
                    loops = 1
                else:
                    loops = int(round(duration/5))
                    final_duration = duration / loops
                for current_loop in range(loops):
                    print("Trigger sleep 1: status: %s duration: %s, final_duration: %s loops: %s, current loop: %s" %
                          (self.scenes_running[scene_id], duration, final_duration, loops, current_loop))
                    yield sleep(final_duration)
                    if self.scenes_running[scene_id] != "running":  # a way to kill this trigger
                        self.scenes_running[scene_id] = "stopped"
                        return False

            elif item['item_type'] == "scene":
                print("starting do_trigger. scene 1")

                scene = self.get(item['machine_label'])
                action = item['action']
                if action == 'enable':
                    self.enable(scene.scene_id)
                elif action == 'disable':
                    self.disable(scene.scene_id)
                elif action == 'start':
                    try:
                        self.trigger(scene.scene_id)
                    except Exception:  # Gobble everything up..
                        pass
                elif action == 'stop':
                    try:
                        self.stop_trigger(scene.scene_id)
                    except Exception:  # Gobble everything up..
                        pass

            elif item['item_type'] == "state":
                self._States.set(item['name'], item['value'], item['value_type'])

            elif item['item_type'] == "template":
                self.scene_templates["%s_%s" % (scene_id, item_id)].render()

            if self.scenes_running[scene_id] != "running":  # a way to kill this trigger
                self.scenes_running[scene_id] = "stopped"
                return False

        self.scenes_running[scene_id] = "stopped"

    def stop_trigger(self, scene_id, **kwargs):
        """
        Trigger a scene to start.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.scenes.get(scene_id)
        if scene_id in self.scenes_running and self.scenes_running[scene_id] == "running":
            self.scenes_running[scene_id] = "stopping"
            return True
        return False

    def patch_scene(self, scene):
        """
        Adds additional attributes and methods to a node instance.

        :param scene:
        :return:
        """
        scene.scene_id = scene._node_id
        scene._Scene = self

        def add_scene_item(node, **kwargs):
            results = node._Scene.add_scene_item(node._node_id, **kwargs)
            return results

        @inlineCallbacks
        def delete(node, session):
            print("about to delete nodeid: %s" % node._node_id)
            results = yield node._Scene.delete(node._node_id, session=session)
            return results

        def description(node):
            return node.data['config']['description']

        def disable(node, session):
            print("about to disable nodeid: %s" % node._node_id)
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
            results = node._Scene.enable(node._node_id, session=session)
            return results

        def stop_trigger(node):
            results = node._Scene.stop_trigger(node._node_id)
            return results

        def trigger(node):
            results = node._Scene.trigger(node._node_id)
            return results


        scene.add_scene_item = types.MethodType(add_scene_item, scene)
        scene.delete = types.MethodType(delete, scene)
        scene.description = types.MethodType(description, scene)
        scene.disable = types.MethodType(disable, scene)
        scene.effective_status = types.MethodType(effective_status, scene)
        scene.enabled = types.MethodType(enabled, scene)
        scene.enable = types.MethodType(enable, scene)
        scene.trigger = types.MethodType(trigger, scene)
        scene.stop_trigger = types.MethodType(stop_trigger, scene)
