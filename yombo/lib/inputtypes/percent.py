"""
Validation of floats. Optionally, will try to convert the input to a float if allowed.
"""
from yombo.lib.inputtypes._input_type import Input_Type

class Percent(Input_Type):

    def validate(self, value, **kwargs):
        try:
            value = float(value)
        except:
            try:
                value = int(value)
            except:
                raise AssertionError("Input is not a percent, must be an int or float.")

        if value < 0:
            raise AssertionError("A percent must be between 0 and 100.")
        if value > 100:
            raise AssertionError("A percent must be between 0 and 100.")

        return value