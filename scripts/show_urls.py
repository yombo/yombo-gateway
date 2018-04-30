#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import netifaces
from os.path import dirname, abspath

print("Access Yombo Gateway:")

internal_hostname = None
interfaces = netifaces.interfaces()
for i in interfaces:
    if i == 'lo':
        continue
    iface = netifaces.ifaddresses(i).get(netifaces.AF_INET)
    if iface != None:
        for j in iface:
            internal_hostname = str(j['addr'])

def show_on_error():
    print("  On local machine:")
    print("   \033[32;1mhttp://127.0.0.1:8080\033[0m")
    if internal_hostname is not None:
        print("")
        print("  On local network:")
        print("   \033[32;1mhttp://%s:8080\033[0m" % internal_hostname)

try:
    yombo_path = dirname(dirname(dirname(abspath(__file__))))
    config_parser = configparser.ConfigParser()
    config_parser.read('%s/yombo.ini' % yombo_path)
    dns_fqdn = config_parser.get('dns', 'fqdn', fallback=None)
    internal_hostname = config_parser.get('core', 'localipaddress_v4', fallback=internal_hostname)
    external_hostname = config_parser.get('core2', 'externalipaddress_v4')
    nonsecure_port = config_parser.get('webinterface', 'nonsecure_port', fallback=8080)
    secure_port = config_parser.get('webinterface', 'secure_port', fallback=8443)
except IOError as e:
    show_on_error()
    exit()
except configparser.NoSectionError:
    show_on_error()
    exit()


if dns_fqdn is None:
    local_hostname = "127.0.0.1"
    local = "http://%s:%s" % (local_hostname, nonsecure_port)
    internal = "http://%s:%s" % (internal_hostname, nonsecure_port)
    external = "https://%s:%s" % (external_hostname, secure_port)
    print("  On local machine:")
    print("   \033[32;1m%s\033[0m" % local)
    print("")
    print("  On local network:")
    print("   \033[32;1m%s\033[0m" % internal)
    print("")
    print("  From external network (check port forwarding):")
    print("   \033[32;1m%s\033[0m" % external)
else:
    website_url = "http://%s" % dns_fqdn
    print("  From anywhere:")
    print("   \033[32;1m%s\033[0m" % website_url)
