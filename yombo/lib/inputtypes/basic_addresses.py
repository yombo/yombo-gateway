from yombo.ext.validators import email
from yombo.lib.inputtypes.string import String
from yombo.lib.inputtypes._input_type import Input_Type



class Email(Input_Type):
    MIN = 5
    MAX = 128

    def validate(self, value, **kwargs):
        print("email 11111")
        value = super(Email, self).validate(value, **kwargs)

        if email(value) is True:
            return value
        else:
            raise AssertionError("Invalid email address.")
