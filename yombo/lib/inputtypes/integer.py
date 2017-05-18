"""
Validation of floats. Optionally, will try to convert the input to a float if allowed.
"""
from yombo.lib.inputtypes._input_type import Input_Type

class Integer(Input_Type):

    def validate(self, value, **kwargs):
        if isinstance(value, int) is False:
            if self.CONVERT is True or 'convert' in kwargs:
                try:
                    value = int(value)
                except:
                    raise AssertionError("Input is not an int.")

        if min in kwargs:
            min = int(kwargs['min'])
        else:
            min = self.MIN

        if max in kwargs:
            max = int(kwargs['max'])
        else:
            max = self.MAX

        if min is not None and value < min:
            raise AssertionError("Value too low. Min: %s" % min)
        if max is not None and value > max:
            raise AssertionError("Value too hight. Max: %s" % max)
