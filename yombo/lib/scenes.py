# doesn't exist on gw
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
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import random_string

logger = get_logger("library.scenes")


class Scenes(YomboLibrary, object):
    """
    Handles activities relating to scenes.
    """
    def __contains__(self, scene_requested):
        """
        Checks to if a provided scenes id, label, or machine_label exists.

            >>> if '137ab129da9318' in self._Scenes:

        or:

            >>> if 'tv time' in self._Scenes:

        :raises YomboWarning: Raised when request is malformed.
        :param scene_requested: The scene ID, label, or machine_label to search for.
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
        .. note::

           The scene must be enabled to be found using this method. An alternative,
           but equal function is: :py:meth:`get() <Scenes.get>`

        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._Scenes['137ab129da9318']  #by id

        or:

            >>> off_cmd = self._Scenes['Off']  #by label & machine_label

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param scene_requested: The scene ID, label, or machine_label to search for.
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
        self.gateway_id = self._Configs.get2("core", "gwid", "local", False)

    def _load_(self, **kwargs):
        """
        Gets scene nodes.

        :return:
        """
        self.scenes = self._Nodes.search({'node_type': 'scene'})
        for scene_id, scene in self.scenes.items():
            self.patch_scene(scene)

    def get(self, requested_scene):
        """
        Return the requested scene, if it's found.

        :param requested_scene:
        :return:
        """
        if requested_scene in self.scenes:
            return self.scenes[requested_scene]
        for temp_scene_id, scene in self.scenes.items():
            if scene.label.lower() == requested_scene.lower():
                return scene
        raise KeyError("Cannot find scene for key: %s" % requested_scene)

    def trigger(self, scene_id, **kwargs):
        """
        Trigger a scene to start.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.scenes[scene_id]
        items = self.get_scene_item(scene_id)
        for item_id, item in items.items():
            if item['item_type'] == "device":
                print("trigger doing device..")
                device = self._Devices[item['device_id']]
                command = self._Commands[item['command_id']]
                inputs = item['inputs']
                device.command(cmd=command,
                               requested_by={'user_id': "System", "component": "yombo.lib.scenes"},
                               control_method='scene',
                               inputs=item['inputs'],
                               **kwargs)
            elif item['item_type'] == "state":
                print("trigger doing state..")
                self._States.set(item['name'], item['value'], item['value_type'])


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

    def patch_scene(self, scene):
        """
        Adds additional attributes and methods to a node instance.

        :param scene:
        :return:
        """
        scene.scene_id = scene._node_id

        @inlineCallbacks
        def delete(target, session):
            print("about to delete nodeid: %s" % target._node_id)
            results = yield target._Parent.delete_node(target._node_id, session=session)
            return results

        @inlineCallbacks
        def disable(target, session):
            print("about to disable nodeid: %s" % target._node_id)
            results = yield target._Parent.disable_node(target._node_id, session=session)
            return results

        @inlineCallbacks
        def enable(target, session):
            print("about to enable nodeid: %s" % target._node_id)
            results = yield target._Parent.enable_node(target._node_id, session=session)
            return results

        @inlineCallbacks
        def add_scene_item(target, **kwargs):
            results = yield target._Parent.add_scene_item(target._node_id, **kwargs)
            return results

        scene.delete = types.MethodType(delete, scene)
        scene.disable = types.MethodType(disable, scene)
        scene.enable = types.MethodType(enable, scene)
        scene.add_scene_item = types.MethodType(add_scene_item, scene)

    def balance_weights(self, scene_id):
        if scene_id not in self.scenes:
            return
        scene = self.scenes[scene_id]
        items = copy.deepcopy(scene.data['items'])
        o_items = OrderedDict(sorted(items.items(), key=lambda x: x[1]['weight']))
        weight = 0
        for item_id, item in o_items.items():
            item['weight'] = weight
            weight += 10
        scene.data['items'] = o_items

    @inlineCallbacks
    def add(self, label, machine_label, status=None):
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
        #     'config': {},
        # }
        self.check_duplicate_scene(label, machine_label)
        data = {
            'items': {},
            'config': {},
        }
        print("scenes:: add 4")
        if status is None:
            status = 1
        new_scene = yield self._Nodes.create(label=label,
                                             machine_label=machine_label,
                                             node_type='scene',
                                             data=data,
                                             data_content_type='json',
                                             gateway_id=self.gateway_id(),
                                             destination='gw',
                                             status=status)
        self.patch_scene(new_scene)
        self.scenes[new_scene.node_id] = new_scene
        return new_scene

    def edit(self, scene_id, label=None, machine_label=None, status=None):
        """
        Edit a scene label and machine_label.

        :param scene_id:
        :param label:
        :param machine_label:
        :param status:
        :return:
        """
        if label is not None and machine_label is not None:
            self.check_duplicate_scene(label, machine_label, scene_id)

        scene = self.scenes[scene_id]
        if label is not None:
            scene.label = label
        if machine_label is not None:
            scene.machine_label = machine_label
        if status is not None and status >= 0 and status <= 2:
            scene.status = status
        return scene

    def get_scene_item(self, scene_id, item_id=None):
        """
        Get a scene item.

        :param scene_id:
        :param item_id:
        :return:
        """
        scene = self.scenes[scene_id]
        if item_id is None:
            return OrderedDict(sorted(scene.data['items'].items(), key=lambda x: x[1]['weight']))
        else:
            return scene.data['items'][item_id]

    def add_scene_item(self, scene_id, **kwargs):
        """
        Add new scene item.

        :param scene_id:
        :param kwargs:
        :return:
        """
        scene = self.scenes[scene_id]
        item_type = kwargs['item_type']
        if 'order' not in kwargs:
            kwargs['order'] = len(scene.data['items'])

        item_id = random_string(length=15)
        if item_type == 'state':
            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'state',
                'name': kwargs['name'],
                'value': kwargs['value'],
                'value_type': kwargs['value_type'],
                'weight': kwargs['weight'],
            }

        elif item_type == 'device':
            device = self._Devices[kwargs['device_id']]
            command = self._Commands[kwargs['command_id']]
            scene.data['items'][item_id] = {
                'item_id': item_id,
                'item_type': 'device',
                'device_id': device.device_id,
                'command_id': command.command_id,
                'inputs': kwargs['inputs'],
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
        scene = self.scenes[scene_id]
        item = scene.data['items'][item_id]

        item_type = item['item_type']

        if item_type == 'state':
            item['name'] = kwargs['name']
            item['value'] = kwargs['value']
            item['value_type'] = kwargs['value_type']
            item['weight'] = kwargs['weight']
        elif item_type == 'device':
            device = self._Devices[kwargs['device_id']]
            command = self._Commands[kwargs['command_id']]
            item['device_id'] = device.device_id
            item['command_id'] = command.command_id
            item['inputs'] = kwargs['inputs']
            item['weight'] = kwargs['weight']
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
        scene = self.scenes[scene_id]
        del scene.data['items'][item_id]
        self.balance_weights(scene_id)
        return scene
