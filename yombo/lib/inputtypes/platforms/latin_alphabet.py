import re

from yombo.lib.inputtypes.platforms.basic_types import String_


class LatinAlphabet(String_):

    def validate(self, value, **kwargs):
        value = super(LatinAlphabet, self).validate(value, **kwargs)
        if re.match(r"[A-Za-z]{3,}", value):  # don't use isalnum, might be blank.
            return value

        raise AssertionError("Value is not within the latin alphabet.")


class LatinAlphanumeric(String_):

    def validate(self, value, **kwargs):
        value = super(LatinAlphabet, self).validate(value, **kwargs)
        if re.match(r"[A-Za-z0-9]{3,}", value):  # don't use isalnum, might be blank.
            return value

        raise AssertionError("Value is not within the latin alphabet or 0-9.")