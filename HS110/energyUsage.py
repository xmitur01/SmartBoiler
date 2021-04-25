"""
Implementation of power usage monitoring service. Used with socket Tp-Link HS110

author: J.Mitura (xmitur01)
version: 1.0
"""
import kasa
import time
import asyncio
import paho.mqtt.client as mqtt
import os
import sys


def getEnergyUsage():
    """Query plug for energy usage data. Runs as async task.

    :return: json with device energy data
    """
    energy_data = asyncio.run(plug.get_emeter_realtime())

    return energy_data


def connectMQTT():
    """Connect to MQTT server and display server IP when successful. If error occur restart script.
    """
    try:
        mqttClient.connect(mqttServerIP)
        print("Connected to %s MQTT broker" % mqttServerIP)
    except OSError:
        print("Failed to connect to MQTT broker. Restarting and reconnecting.")
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)


def initialize():
    """Initialize MQTT client and smart plug device instance

    :return: tuple[MQTT client object,
             smart plug object]
    """
    client = mqtt.Client(client_id=clientID)

    p = kasa.SmartPlug(plugIP)
    asyncio.run(p.update())

    return client, p


def sentPayload(name, site, value):
    """Publishes message on MQTT server.

    :param name: string record name
    :param site: string location
    :param value: float wat hours
    """
    payload = name + ',site=%s value=%s' % (site, value)
    mqttClient.publish(topic=mqttPublishTopic, payload=payload)


def publish():
    """Main script cycle(check connection, get data, send sata).
    Every 5 seconds tries to send data with energy consumption and actual power state on MQTT server
    if connection is up.
    """
    while True:
        mqttClient.reconnect()

        energy_data = getEnergyUsage()
        wats = float(energy_data['power_mw']) / 1000
        wat_hours = float(energy_data['total_wh'])

        sentPayload(name="power", site="bathroom", value=wats)
        sentPayload(name="energy_total", site="bathroom", value=wat_hours)

        time.sleep(updateInterval)


# ===================================== #
#                 MAIN                  #
# ===================================== #

mqttPublishTopic = 'sensors'
clientID = 'HS110_boiler'
mqttServerIP = '192.168.1.105'  # change to Your MQTT IP
updateInterval = 5

plugIP = "192.168.1.100"    # change to Your socket IP

mqttClient, plug = initialize()
connectMQTT()

publish()
