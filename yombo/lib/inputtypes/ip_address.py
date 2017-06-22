from yombo.ext.ipy import IP
from yombo.lib.inputtypes.input_type import Input_Type

class IP_Address(Input_Type):

    IP_PRIVATE = None
    IP_PUBLIC = None
    IP_V4 = None
    IP_V6 = None

    def validate(self, value, **kwargs):
        try:
            ip = IP(value)
        except:
            raise AssertionError("Invalid IP address")

        if self.IP_PRIVATE is not None:
            if ip.iptype() != "PRIVATE":
                raise AssertionError("Invalid IP address - not private")

        if self.IP_PUBLIC is not None:
            if ip.iptype() != "PUBLIC":
                raise AssertionError("Invalid IP address - not public")

        if self.IP_V4 is not None:
            if ip.version() != 4:
                raise AssertionError("Invalid IP address - not version 4")

        if self.IP_V6 is not None:
            if ip.version() != 6:
                raise AssertionError("Invalid IP address - not version 6")

        if "raw" in kwargs:
            return ip
        return ip.strNormal()


class IP_Address_Private(IP_Address):

    IP_PRIVATE = True


class IPv4_Address(IP_Address):

    IP_V4 = True


class IP_Address_Public(IP_Address):

    IP_PUBLIC = True


class IPv4_Address_Private(IP_Address):

    IP_PRIVATE = True
    IP_V4 = True


class IPv4_Address_Public(IP_Address):

    IP_PUBLIC = True
    IP_V4 = True


class IPv6_Address(IP_Address):

    IP_V6 = True


class IPv6_Address_Private(IP_Address):

    IP_PRIVATE = True
    IP_V6 = True


class IPv6_Address_Public(IP_Address):

    IP_PUBLIC = True
    IP_V6 = True


