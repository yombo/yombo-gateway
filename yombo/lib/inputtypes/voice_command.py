from yombo.lib.inputtypes._input_type import Input_Type


class Voice_Command(Input_Type):

    def validate(self, value, **kwargs):
        if value in self._Parent._VoiceCmds:
            return value
        raise AssertionError("Invalid voice command input.")
