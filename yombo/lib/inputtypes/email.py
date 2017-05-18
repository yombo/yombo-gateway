from yombo.ext.validators import email
from yombo.lib.inputtypes.string import String


class Email(String):
    MIN = 5
    MAX = 128

    def validate(self, value, **kwargs):
        value = super(Password, self).validate(value, **kwargs)

        if email(value) is True:
            return value
        else:
            raise AssertionError("Invalid email address.")
