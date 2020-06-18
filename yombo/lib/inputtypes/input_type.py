"""
Base input type validator.
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/inputtypes/input_type.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.inputtypes.validator")


class InputType(Entity, LibraryDBChildMixin):
    """
    A class to manage a single input type.
    :ivar input_type_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created: (int) EPOCH time when created
    :ivar updated: (int) EPOCH time when last updated
    """
    ALLOW_BLANK = True
    ALLOW_NONE = True
    ALLOW_NULL = True

    MIN = None
    MAX = None
    CONVERT = True

    _Entity_type: ClassVar[str] = "Input type"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    def to_dict_postprocess(self, data, to_database: Optional[bool] = None, **kwargs):
        """
        Add 'is_usable' attribute if not sending to the database.

        :param to_database:
        :return:
        """
        if to_database in (True, None):
            return
        data["is_usable"] = self.is_usable

    def validate(self, input, **kwargs):
        logger.warn("Input type doesn't have a validator. Accepting input by default. '{machine_label}",
                    machine_label=self.machine_label)
        return input

    def pre_validate(self, value, **kwargs):
        return value

    def validate(self, value, **kwargs):
        if value is None:
            if self.ALLOW_NULL is False and "allow_none" not in kwargs:
                if "default" in kwargs:
                    return kwargs["default"]
                raise AssertionError("NoneType not allowed")
        if value is "":
            if self.ALLOW_BLANK is False and "allow_blank" not in kwargs:
                raise AssertionError("Blank (non-None) not allowed")

        return value

    def check_min_max(self, value, **kwargs):
        if "min" in kwargs and kwargs["min"] is not None:
            min = int(kwargs["min"])
        else:
            min = self.MIN

        if "max" in kwargs and kwargs["max"] is not None:
            max = int(kwargs["max"])
        else:
            max = self.MAX

        count_types = (str, list, dict, tuple)
        if isinstance(value, count_types):
            length = len(value)
            if min is not None and length < min:
                raise AssertionError("Value is too short.")
            if max is not None and length > max:
                raise AssertionError("Value is too long.")
        else:
            if min is not None and value < min:
                raise AssertionError(f"Value too low. Min: {min}")
            if max is not None and value > max:
                raise AssertionError(f"Value too high. Max: {max}")