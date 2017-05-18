from yombo.lib.inputtypes._input_type import Input_Type

class _Any(Input_Type):

    def validate(self, value, **kwargs):
        return value
