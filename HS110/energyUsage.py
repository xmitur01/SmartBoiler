import kasa
import time
import asyncio
import paho.mqtt.client as mqtt
import os
import sys

# async def turnOff():
#     await plug.turn_off()
#
#
# async def turnOn():
#     await plug.turn_on()


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
    asyncio.run(p.update())

    return client, p


def publish():
    while True:
        energy_data = getEnergyUsage()
        wats = float(energy_data['power_mw']) / 1000
        print(str(wats) + " W")

        payload = 'power,site=%s value=%s' % ("bathroom", wats)
        mqttClient.publish(topic=mqttPublishTopic, payload=payload)

        time.sleep(updateInterval)


mqttPublishTopic = 'sensors'
clientID = 'HS110_boiler'
mqttServerIP = '192.168.1.105'
updateInterval = 5

plugIP = "192.168.1.104"

mqttClient, plug = initialize()
connectMQTT()
publish()
