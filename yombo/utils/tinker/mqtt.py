#!/usr/bin/env python3
"""
Test mqtt connections to the gateway.

"""
gateway_id = "gn16m4W7z9t9cZOx4Apyar"
mqtt_auth = "fpL6YT4QL3kIpanRsCviX0lrCBhMOFPBr8IWytvO4hq1N"


# No need to edit below here.





import asyncio
import hashlib
import signal
import time

from gmqtt import Client as MQTTClient

# gmqtt also compatibility with uvloop
# import uvloop
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


STOP = asyncio.Event()
username = f"yombogw-{gateway_id}"


def on_connect(client, flags, rc, properties):
    print(f'Connected: flags: {flags}')
    print(f' -- rc: {rc}')
    print(f' -- properties: {properties}')
    print('Subscribing')
    client.subscribe('yombo/#', qos=1, subscription_identifier=222)
    client.subscribe('test/#', qos=1, subscription_identifier=222)


def on_message(client, topic, payload, qos, properties):
    print(f"RECV MSG: {topic} - {qos}")
    print(f" - Properties: {properties}")
    print(f" - {payload}")


def on_disconnect(client, packet, exc=None):
    print(f"Disconnected: {client} - {packet} - {exc}")
    print('Disconnected')


def on_subscribe(client, mid, qos, properties):
    print(f"SUBSCRIBED: {client} - {mid} - {qos} - {properties}")


def ask_exit(*args):
    STOP.set()


async def main(broker_host, username, password):
    client = MQTTClient("client-id-mitch", user_property=('hello', 'there'))
    # client = MQTTClient("client-id-mitch")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe

    client.set_auth_credentials(username, password.encode())
    await client.connect(host=broker_host, port=1883)
    # await client.connect()
    print("connected, now ready to send...")
    data = f"This is a test! {str(time.time())}"
    hash = hashlib.sha256(data.encode()).hexdigest()
    client.publish('test/time1', "hello test/time1..", qos=1,
                   message_expiry_interval=5,
                   content_type="json",
                   response_topic='RESPONSE/TOPIC2',
                   user_property=[('hash', hash), ('time', str(time.time()))])
    client.publish('test/time2', "hello test/time2..", qos=1,
                   message_expiry_interval=5,
                   content_type="json",
                   response_topic='RESPONSE/TOPIC',
                   user_property=[('hash', hash), ('time', str(time.time()))])

    await STOP.wait()
    await client.disconnect()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    host = 'localhost'

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    loop.run_until_complete(main(host, username, mqtt_auth))