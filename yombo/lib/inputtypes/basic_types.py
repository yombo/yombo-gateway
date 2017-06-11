"""
Validation of floats. Optionally, will try to convert the input to a float if allowed.
"""
from yombo.lib.inputtypes._input_type import Input_Type

class _Float(Input_Type):

    def validate(self, value, **kwargs):
        if isinstance(value, float):
            return value
        else:
            if self.CONVERT is True or 'convert' in kwargs:
                try:
                    return float(value)
                except:
                    if 'allow_int' in kwargs:
                        try:
                            return int(value)
                        except:
                            pass
        raise AssertionError("Input is not a float.")

