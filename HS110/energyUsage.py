import kasa
import time
import asyncio
import paho.mqtt.client as mqtt
import os
import sys


def getEnergyUsage():
    energy_data = asyncio.run(plug.get_emeter_realtime())

    return energy_data


def connectMQTT():
    try:
        mqttClient.connect(mqttServerIP)
        print("Connected to %s MQTT broker" % mqttServerIP)
    except OSError:
        print("Failed to connect to MQTT broker. Reconnecting...")
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)


def initialize():
    client = mqtt.Client(client_id=clientID)

    p = kasa.SmartPlug(plugIP)
    asyncio.run(p.update()) # move async outside function into try expect with wait till success

    return client, p


def sentPayload(name, site, value):
    payload = name + ',site=%s value=%s' % (site, value)
    mqttClient.publish(topic=mqttPublishTopic, payload=payload)


def publish():
    # remove while cycle 
    while True:
        energy_data = getEnergyUsage()
        wats = float(energy_data['power_mw']) / 1000
        wat_hours = float(energy_data['total_wh'])

        # print(str(wats) + " W")
        # print(str(wat_hours) + " Wh")

        sentPayload(name="power", site="bathroom", value=wats)
        sentPayload(name="energy_total", site="bathroom", value=wat_hours)

        time.sleep(updateInterval)


mqttPublishTopic = 'sensors'
clientID = 'HS110_boiler'
mqttServerIP = '192.168.1.105'  # change to Your MQTT IP
updateInterval = 5

plugIP = "192.168.1.100"    # change to Your socket IP
 
mqttClient, plug = initialize()
connectMQTT()
# put while cycle here + check connection to MQTT and socket online
publish()
