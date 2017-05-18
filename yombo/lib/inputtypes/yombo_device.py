from yombo.lib.inputtypes._input_type import Input_Type


class Yombo_Device(Input_Type):

    def validate(self, value, **kwargs):
        if value in self._Parent._Devices:
            return value
        raise AssertionError("Invalid yombo device.")
