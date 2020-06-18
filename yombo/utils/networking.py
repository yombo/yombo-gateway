"""
Various tools for working with networking information.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo.
:license: See LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/networking.html>`_
"""
import binascii
import netifaces
import netaddr
from struct import pack as struct_pack, unpack as struct_unpack
import socket
from urllib.parse import urlparse

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks

from yombo.utils.decorators import cached


@inlineCallbacks
def test_url_listening(url: str):
    """
    Tries to check if a server is listening at the URL. Returns True/False. If the port number cannot be derived
    from the url, a ValueError will be raise.

    If you have the host and port number, use test_port_listening instead.

    :param url: The full url to check for.
    :return:
    """
    parts = urlparse(url)
    scheme = parts.scheme
    host = parts.netloc
    if scheme is None or host is None:
        raise SyntaxWarning("Invalid URL format.")

    port = parts.port
    if port is None:  # Try to guess port number
        if scheme == "ftp":
            port = 21
        elif scheme == "ssh":
            port = 22
        elif scheme == "telnet":
            port = 23
        elif scheme == "smtp":
            port = 25
        elif scheme == "tfpt":
            port = 69
        elif scheme == "http":
            port = 80
        elif scheme == "https":
            port = 443

    if port is None:
        raise ValueError("Port number not found, ensure to include")
    results = yield test_port_listening(host, port)
    return results


@inlineCallbacks
def test_port_listening(host: str, port: int) -> bool:
    """
    Returns a deferred whose result will be True/False.

    Tests if port is open on the host.

    :param host:
    :param port:
    :return:
    """
    results = yield threads.deferToThread(_test_port_listening, host, port)
    return results


def _test_port_listening(host, port):
    """
    Should only be called by it's parent 'test_port_listening' due to blocking.
    :return:
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    return sock.connect_ex((host, port)) == 0


@cached(600)
def get_local_network_info(ethernet_name=None):
    """
    Collects various information about the local network.
    From: http://stackoverflow.com/questions/3755863/trying-to-use-my-subnet-address-in-python-code
    :return:
    """

    gws = netifaces.gateways()
    if ethernet_name is not None:
        myiface = ethernet_name
    else:
        myiface = gws["default"][netifaces.AF_INET][1]

    gateway_v4 = list(gws["default"].values())[0][0]

    addrs = netifaces.ifaddresses(myiface)

    # Get ipv4 stuff
    ipinfo = addrs[socket.AF_INET][0]
    address_v4 = ipinfo["addr"]
    netmask_v4 = ipinfo["netmask"]
    # Create ip object and get
    cidr_v4 = netaddr.IPNetwork(f"{address_v4}/{netmask_v4}")
    network_v4 = cidr_v4.network

    try:
        ipinfo = addrs[socket.AF_INET6][0]
        address_v6 = ipinfo["addr"].split("%")[0]
        netmask_v6 = ipinfo["netmask"]
    except KeyError:
        address_v6 = None
        netmask_v6 = None

    return {"ipv4":
                {
                    "address": str(address_v4), "netmask": str(netmask_v4), "cidr": str(cidr_v4),
                    "network": str(network_v4), "gateway": str(gateway_v4)
                },
            "ipv6":
                {"address": str(address_v6), "netmask": str(netmask_v6), "gateway": str("")}
            }


@cached(600)
def ip_address_in_local_network(ip_address):
    """ Checks if a given IP address belongs to the local network. """
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

    return ip_lower <= ip_integer <= ip_upper


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

            return ip_integer, 4 if version == socket.AF_INET else 6
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
    """ Convet an ip address to a large integer. """
    return struct_unpack("!I", socket.inet_aton(address))[0]


def int_to_ip_address(address):
    """ Convert a large integer to an IP address. """
    return socket.inet_ntoa(struct_pack("!I", address))
