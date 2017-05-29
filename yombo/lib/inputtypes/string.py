from yombo.lib.inputtypes._input_type import Input_Type


class String(Input_Type):

    def validate(self, value, **kwargs):
        if min in kwargs:
            min = int(kwargs['min'])
        else:
            min = self.MIN

        if max in kwargs:
            max = int(kwargs['max'])
        else:
            max = self.MAX

        if isinstance(value, str):
            length = len(value)
            if min is not None and length < min:
                raise AssertionError("Password is too short.")
            if max is not None and length > max:
                raise AssertionError("Password is too long.")

            return value
        else:
            if self.CONVERT is True or 'convert' in kwargs:
                if value is None:
                    if self.ALLOW_NONE is True or 'allow_none' in kwargs:
                        return "None"
                return str(value)
        raise AssertionError("Invalid value, item is a not a string.")
