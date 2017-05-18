"""
Base input type validator.

"""
class Input_Type(object):
    ALLOW_NONE = True
    ALLOW_BLANK = True

    MIN = None
    MAX = None
    CONVERT = None

    def __init__(self, parent):
        self._Parent = parent

    def validate(self, value, **kwargs):
        if value is None:
            if self.ALLOW_NULL is False and 'allow_none' not in kwargs:
                raise AssertionError("NoneType not allowed")
        if value is "":
            if self.ALLOW_BLANK is False and 'allow_blank' not in kwargs:
                raise AssertionError("Blank (non-None) not allowed")

        return value

