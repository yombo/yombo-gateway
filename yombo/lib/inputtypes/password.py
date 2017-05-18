from yombo.lib.inputtypes.string import String


class Password(String):
    MIN = 3
    MAX = 64

    def validate(self, value, **kwargs):
        return super(Password, self).validate(value, **kwargs)
