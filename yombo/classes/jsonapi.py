"""
Converts Yombo items to JSON API 1.1 spec.


Based on: https://jsonapi.org/

**Usage**:

.. code-block:: python

   from yombo.classes.jsonapi

   jsonapi = JSONApi(data=self._States.get("day_of_week", instance=True)).
   print(jsonapi)
   # {
   #     "data": {
   #         "type": "states",
   #         "id": "day_of_week",
   #         "attributes": {
   #             "id": "day_of_week",
   #             "gateway_id": "gn16m4W7z9t9cZOx4Apyar",
   #             "value": "wednesday",
   #             "value_human": "wednesday",
   #             "value_type": "string",
   #             "request_by": "yombo_system_account",
   #             "request_by_type": "user",
   #             "request_context": "yombo.lib.times:Times",
   #             "last_access_at": 1586378831,
   #             "created_at": 1585472113,
   #             "updated_at": 1586378831
   #         }
   #     }
   # }

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/jsonapi.html>`_
"""
import msgpack
import simplejson as json
from typing import Any, List, Optional, Union


class JSONApi:
    """
    Accepts Yombo items and converts it to a JSON API formatted output.
    """
    def __init__(self, data: Union[List[dict], dict], included: Optional[List[dict]] = None,
                 meta: Optional[dict] = None, links: Optional[dict] = None, data_type: Optional[str] = None,
                 dict_type: Optional[str] = None, output_type: Optional[str] = None):
        """
        Setup the JSONApi with data.

        :param data: A Yombo item, such as a state, device, atom, etc.
        :param included: Like data, but will be used to set the 'included' portion of the response.
        :param meta: Meta items to add to response.
        :param links: Links to add to response.
        :param data_type: Used as a default 'type' for the data items, otherwise tries to glean from the data.
        :param dict_type: Type of dictionary formatter to use, either "to_database" or "to_external". Default: to_external
        :param output_type: Either "dict", "json", or "msgpack", defaults to dict. This is used for render().
        """
        self.data = data
        self.included = included
        self.meta = meta
        self.links = links
        self.dict_type = dict_type
        self.default_data_type = data_type
        if dict_type is None:
            self.dict_type = "to_external"
        self.output_type = output_type

    def __str__(self):
        return self.to_json()

    def render(self):
        """
        Convenience function to get the data, uses the object's output_type to determine the type.
        """
        if self.output_type is None or self.output_type == "dict":
            return self.to_dict()
        else:
            return self.to_json()

    def data_type(self, incoming=None):
        """
        Gleans the data::type from the data. For performance reasons, accepts the output of "to_dict" as input.

        :param incoming:
        :return:
        """
        if self.default_data_type is not None:
            return self.default_data_type
        if incoming is None:
            incoming = self.to_dict()
        return incoming["data"][0]["type"]

    def to_dict(self, dict_type: Optional[str] = None):
        """
        Returns a dictionary representing the data in a JSON API format.

        :param dict_type: Type of dictionary formatter to use, either "to_database" or "to_external". Default: to_external
        :return:
        """
        if dict_type is None:
            dict_type = self.dict_type
        output = {}
        if isinstance(self.links, dict):
            output["links"] = self.links

        def from_object(data, data_type=None):
            """ Processes a Yombo Object, and returns a JSON API section as as dict. """
            if data_type is None:
                data_type = data._Parent._storage_attribute_name
            return {
                "type": data_type,
                "id": data._primary_field_id,
                "attributes": data.to_external() if dict_type == "to_external" else data.to_database(),
            }

        def from_dict(data, data_type=None):
            """ Processes a specially formatted dictionary, and returns a JSON API section as as dict. """
            if data_type is None:
                data_type = data["type"]
            return {
                "type": data_type,
                "id": data["id"],
                "attributes": data["attributes"],
            }

        def processing_incoming(portion, data_type):
            """
            Parses the 'data' portion and 'included' portion, and sends it to from_object or from_dict.
            :return:
            """
            if isinstance(portion, list):
                results = []
                for item in portion:
                    if isinstance(item, dict):
                        results.append(from_dict(item, data_type))
                    else:
                        results.append(from_object(item, data_type))
                return results
            elif isinstance(portion, dict):
                return from_dict(portion)
            else:
                return from_object(portion)

        output["data"] = processing_incoming(self.data, self.default_data_type)
        if isinstance(self.included, dict):
            output["included"] = processing_incoming(self.included, self.default_data_type)

        if isinstance(self.meta, dict):
            output["meta"] = self.meta
        return output

    def to_json(self, dict_type: Optional[str] = None):
        """
        Returns the data in JSON format.

        :param dict_type: Type of dictionary formatter to use, either "to_dict" or "to_external". Default: to_external
        :return:
        """
        return json.dumps(self.to_dict(dict_type))

    def to_msgpack(self, dict_type: Optional[str] = None):
        """
        Returns the data in msgpack format.

        :param dict_type: Type of dictionary formatter to use, either "to_dict" or "to_external". Default: to_external
        :return:
        """
        return msgpack.packb(self.to_dict(dict_type))
