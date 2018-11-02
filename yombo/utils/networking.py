"""
Various tools for detailing with networking information.
"""
import binascii
import netifaces
import netaddr
import socket
from struct import pack as struct_pack, unpack as struct_unpack

from yombo.utils.decorators import cached


@cached(600)
def get_local_network_info(ethernet_name = None):
    """
    Collects various information about the local network.
    From: http://stackoverflow.com/questions/3755863/trying-to-use-my-subnet-address-in-python-code
    :return:
    """
    ifaces = netifaces.interfaces()
    # => ["lo", "eth0", "eth1"]

    if ethernet_name is not None:
        myiface = ethernet_name
    else:
        gws = netifaces.gateways()
        myiface = gws["default"][netifaces.AF_INET][1]

    gws = netifaces.gateways()
    gateway_v4 = list(gws["default"].values())[0][0]

    addrs = netifaces.ifaddresses(myiface)
    # {2: [{"addr": "192.168.1.150",
    #             "broadcast": "192.168.1.255",
    #             "netmask": "255.255.255.0"}],
    #   10: [{"addr": "fe80::21a:4bff:fe54:a246%eth0",
    #                "netmask": "ffff:ffff:ffff:ffff::"}],
    #   17: [{"addr": "00:1a:4b:54:a2:46", "broadcast": "ff:ff:ff:ff:ff:ff"}]}

    # Get ipv4 stuff
    ipinfo = addrs[socket.AF_INET][0]
    address_v4 = ipinfo["addr"]
    netmask_v4 = ipinfo["netmask"]
    # Create ip object and get
    cidr_v4 = netaddr.IPNetwork(f"{address_v4}/{netmask_v4}")
    # => IPNetwork("192.168.1.150/24")
    network_v4 = cidr_v4.network

    ipinfo = addrs[socket.AF_INET6][0]
    address_v6 = ipinfo["addr"].split("%")[0]
    netmask_v6 = ipinfo["netmask"]
    # Create ip object and get
    # cidr_v6 = netaddr.IPNetwork("%s/%s" % (address_v6, netmask_v6))
    # => IPNetwork("192.168.1.150/24")
    # network_v6 = cidr_v6.network

    # => IPAddress("192.168.1.0")
    return {"ipv4":
                {"address": str(address_v4), "netmask": str(netmask_v4), "cidr": str(cidr_v4),
                 "network": str(network_v4), "gateway": str(gateway_v4)},
            "ipv6":
                {"address": str(address_v6), "netmask": str(netmask_v6), "gateway": str("")},
            }


@cached(600)
def ip_addres_in_local_network(ip_address):
    local_network = get_local_network_info()
    try:
        if ip_address_in_network(ip_address, local_network["ipv4"]["cidr"]):
            return True
    except:
        pass
    try:
        if ip_address_in_network(ip_address, local_network["ipv6"]["cidr"]):
            return True
    except:
        pass
    return False


@cached(600)
def ip_address_in_network(ip_address, subnetwork):
    """
    from: https://diego.assencio.com/?index=85e407d6c771ba2bc5f02b17714241e2

    Returns True if the given IP address belongs to the
    subnetwork expressed in CIDR notation, otherwise False.
    Both parameters are strings.

    Both IPv4 addresses/subnetworks (e.g. "192.168.1.1"
    and "192.168.1.0/24") and IPv6 addresses/subnetworks (e.g.
    "2a02:a448:ddb0::" and "2a02:a448:ddb0::/44") are accepted.
    """
    (ip_integer, version1) = ip_to_integer(ip_address)
    (ip_lower, ip_upper, version2) = subnetwork_to_ip_range(subnetwork)

    if version1 != version2:
        raise ValueError("incompatible IP versions")

    return (ip_lower <= ip_integer <= ip_upper)


def ip_to_integer(ip_address):
    """
    from: https://diego.assencio.com/?index=85e407d6c771ba2bc5f02b17714241e2

    Converts an IP address expressed as a string to its
    representation as an integer value and returns a tuple
    (ip_integer, version), with version being the IP version
    (either 4 or 6).

    Both IPv4 addresses (e.g. "192.168.1.1") and IPv6 addresses
    (e.g. "2a02:a448:ddb0::") are accepted.
    """

    # try parsing the IP address first as IPv4, then as IPv6
    for version in (socket.AF_INET, socket.AF_INET6):

        try:
            ip_hex = socket.inet_pton(version, ip_address)
            ip_integer = int(binascii.hexlify(ip_hex), 16)

            return (ip_integer, 4 if version == socket.AF_INET else 6)
        except:
            pass

    raise ValueError("invalid IP address")


def subnetwork_to_ip_range(subnetwork):
    """
    from: https://diego.assencio.com/?index=85e407d6c771ba2bc5f02b17714241e2

    Returns a tuple (ip_lower, ip_upper, version) containing the
    integer values of the lower and upper IP addresses respectively
    in a subnetwork expressed in CIDR notation (as a string), with
    version being the subnetwork IP version (either 4 or 6).

    Both IPv4 subnetworks (e.g. "192.168.1.0/24") and IPv6
    subnetworks (e.g. "2a02:a448:ddb0::/44") are accepted.
    """

    try:
        fragments = subnetwork.split("/")
        network_prefix = fragments[0]
        netmask_len = int(fragments[1])

        # try parsing the subnetwork first as IPv4, then as IPv6
        for version in (socket.AF_INET, socket.AF_INET6):

            ip_len = 32 if version == socket.AF_INET else 128

            try:
                suffix_mask = (1 << (ip_len - netmask_len)) - 1
                netmask = ((1 << ip_len) - 1) - suffix_mask
                ip_hex = socket.inet_pton(version, network_prefix)
                ip_lower = int(binascii.hexlify(ip_hex), 16) & netmask
                ip_upper = ip_lower + suffix_mask

                return (ip_lower,
                        ip_upper,
                        4 if version == socket.AF_INET else 6)
            except:
                pass
    except:
        pass

    raise ValueError("invalid subnetwork")


def ip_address_to_int(address):
    return struct_unpack("!I", socket.inet_aton(address))[0]


def int_to_ip_address(address):
    return socket.inet_ntoa(struct_pack("!I", address))
