from yombo.lib.inputtypes._input_type import Input_Type


class Yombo_Command(Input_Type):

    def validate(self, value, **kwargs):
        if value in self._Parent._Commands:
            return value
        raise AssertionError("Invalid command.")
