"""
Base input type validator.
"""

import types

from yombo.core.log import get_logger
logger = get_logger('library.inputtypes.validator')

class Input_Type(object):
    """
    A class to manage a single input type.
    :ivar input_type_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
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

    def __init__(self, parent, input_type):
        """
        Setup the input type object using information passed in.

        :param input_type: An input type with all required items to create the class.
        :type input_type: dict

        """
        logger.debug("input_type info: {input_type}", input_type=input_type)

        self._Parent = parent
        self.input_type_id = input_type['id']
        self.machine_label = input_type['machine_label']
        self.updated_srv = None

        # below are configure in update_attributes()
        self.category_id = None
        self.label = None
        self.machine_label = None
        self.description = None
        self.input_regex = None
        self.always_load = None
        self.status = None
        self.public = None
        self.created = None
        self.updated = None
        # self.validate = lambda x : x  # is set in the load validators up above.
        self.update_attributes(input_type)

    def validate(self, input, **kwargs):
        logger.warn("Input type doesn't have a validator. Accepting input by default. '{machine_label}",
                    machine_label=self.machine_label)
        return input

    def update_attributes(self, input_type):
        """
        Sets various values from a input type dictionary. This can be called when either new or
        when updating.

        :param input_type: 
        :return: 
        """
        if 'category_id' in input_type:
            self.category_id = input_type['category_id']
        if 'label' in input_type:
            self.label = input_type['label']
        if 'machine_label' in input_type:
            self.machine_label = input_type['machine_label']
        if 'description' in input_type:
            self.description = input_type['description']
        if 'input_regex' in input_type:
            self.input_regex = input_type['input_regex']
        if 'always_load' in input_type:
            self.always_load = input_type['always_load']
        if 'status' in input_type:
            self.status = input_type['status']
        if 'public' in input_type:
            self.public = input_type['public']
        if 'created' in input_type:
            self.created = input_type['created']
        if 'updated' in input_type:
            self.updated = input_type['updated']

    def __str__(self):
        """
        Print a string when printing the class.  This will return the input type id so that
        the input type can be identified and referenced easily.
        """
        return self.input_type_id

    def __repl__(self):
        """
        Export input type variables as a dictionary.
        """
        return {
            'input_type_id': str(self.input_type_id),
            'category_id': str(self.category_id),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'input_regex': str(self.input_regex),
            'always_load': str(self.always_load),
            'public': int(self.public),
            'status': int(self.status),
            'created': int(self.created),
            'updated': int(self.updated),
        }

    def pre_validate(self, value, **kwargs):
        return value

    def validate(self, value, **kwargs):
        if value is None:
            if self.ALLOW_NULL is False and 'allow_none' not in kwargs:
                if 'default' in kwargs:
                    return kwargs['default']
                raise AssertionError("NoneType not allowed")
        if value is "":
            if self.ALLOW_BLANK is False and 'allow_blank' not in kwargs:
                raise AssertionError("Blank (non-None) not allowed")

        return value

    def check_min_max(self, value, **kwargs):
        if 'min' in kwargs and kwargs['min'] is not None:
            min = int(kwargs['min'])
        else:
            min = self.MIN

        if 'max' in kwargs and kwargs['max'] is not None:
            max = int(kwargs['max'])
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
                raise AssertionError("Value too low. Min: %s" % min)
            if max is not None and value > max:
                raise AssertionError("Value too hight. Max: %s" % max)