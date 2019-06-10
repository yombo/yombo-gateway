"""
Base input type validator.
"""

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.inputtypes.validator")


class Input_Type(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
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

    _primary_column = "input_type_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the input type object using information passed in.

        :param incoming: An input type with all required items to create the class.
        :type incoming: dict
        """
        self._Entity_type = "Input type"
        self._Entity_label_attribute = "machine_label"
        super().__init__(parent)

        self._setup_class_model(incoming, source=source)

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