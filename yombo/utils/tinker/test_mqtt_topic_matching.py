#!/usr/bin/env python3
"""
Tests topic matching for mosquitto_auth api.
"""

ACCESS_MAP = {
    1: "read",
    2: "write",
    4: "read",  # This is really subscribe - but to read, you must subscribe.
}

mqtt_users = {
    "tester": {
        "topics": {
            "sometopic/+/1234/#": ['read'],
            "yombo_gw/+/global/#": ['read', 'write'],
            "yombo_gw/+/cluster/#": ['write'],
        }
    }
}


def _topic_search(topic_requested: str, topic_allowed: list) -> bool:
    """
    Attempts to match a requested topic with a list of topics allowed.

    Insipired by: https://github.com/beerfactory/hbmqtt/blob/master/hbmqtt/plugins/topic_checking.py
    """
    req_split = topic_requested.split('/')
    allowed_split = topic_allowed.split('/')
    ret = True
    for i in range(max(len(req_split), len(allowed_split))):
        try:
            req_aux = req_split[i]
            allowed_aux = allowed_split[i]
        except IndexError:
            ret = False
            break
        if allowed_aux == '#':
            break
        elif (allowed_aux == '+') or (allowed_aux == req_aux):
            continue
        else:
            ret = False
            break
    return ret


def topic_match(user: dict, requested_topic: str, access_requested: list) -> bool:
    """
    Match requested topic with user allowed topics. If user has a matching topic, it's access
    it validated.
    """
    access_req = ACCESS_MAP[access_requested]
    allowed_topics = user["topics"]
    print(" ")
    print(f"Topic Match starting: {user['username']} - requested_topic: {requested_topic} - {access_req}")

    if len(requested_topic) < 0:
        return False

    if requested_topic:
        if len(allowed_topics):
            for allowed_topic, allowed_permissions in allowed_topics.items():
                if _topic_search(requested_topic, allowed_topic):
                    print(f"--> topic_matched {requested_topic}- requested perm: {access_req} - allowed: {allowed_permissions}")
                    if access_req in allowed_permissions:
                        return True
            return False
        else:
            return False
    else:
        return False


user = {
    "type": "mqttuser",
    "username": "tester",
    "topics": mqtt_users["tester"]["topics"],
}


print(f"Should be True: {topic_match(user, 'sometopic/abc/1234/boooo', 1)}")
print(f"Should be True: {topic_match(user, 'sometopic/abc/1234/boooo/2asdf', 1)}")
print(f"Should be False: {topic_match(user, 'sometopic/abc/333/boooo/2asdf', 1)}")
print(f"---> Should be False (wrong access): {topic_match(user, 'yombo_gw/abc/cluster/2323', 1)}")
print(f"---> Should be True: {topic_match(user, 'yombo_gw/abc/cluster/2323', 2)}")
print(f"Should be False: {topic_match(user, 'sometopic/abc/d1234/boooo', 1)}")

