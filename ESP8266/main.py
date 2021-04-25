from umqtt.robust import MQTTClient
import machine
import utime as time
import gc
import onewire
import ds18x20
import esp
from struct import unpack

import boot

mqttPublishTopic = 'sensors'
clientID = 'esp32-01'
mqttServerIP = '192.168.1.105'  # change to Your MQTT IP

lastMessage = 0
messageInterval = 5

previous_pipe_temp = None


def connectMQTT():
    client.reconnect()
    print('Connected to %s MQTT broker' % mqttServerIP)


def restartAndReconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    time.sleep(10)
    machine.reset()


def checkWifi():
    connection_lost = False

    while not boot.station.isconnected():
        time.sleep_ms(500)
        connection_lost = True
        boot.station.connect()

    if connection_lost:
        client.reconnect()


def decodeByteArray(byte_arr):
    value = unpack('<H', byte_arr)[0]
    if value == 32040:
        return "pipe"
    else:
        return "tank"


def readSensor():
    try:
        roms = dsSensor.scan()
        dsSensor.convert_temp()
        time.sleep_ms(750)
        sensors_temperatures = []

        for rom in roms:
            sensor_temp = dsSensor.read_temp(rom)

            if isinstance(sensor_temp, float) or (isinstance(sensor_temp, int)):
                reformat_temp = ('{0:3.1f}'.format(sensor_temp))
                sensors_temperatures.append([decodeByteArray(byte_arr=rom), reformat_temp])
            else:
                print('Invalid sensor readings.')
                return []

        return sensors_temperatures
    except OSError:
        print('Failed to read sensor.')
        restartAndReconnect()


def publishWaterUsage(data):
    global previous_pipe_temp

    if previous_pipe_temp is not None:
        if float(data[1]) - float(previous_pipe_temp) > 1.0:
            msg = b'usage,site=%s value=%s' % ("water", 1)
            client.publish(mqttPublishTopic, msg)

        elif float(data[1]) - float(previous_pipe_temp) < 0.0:
            msg = b'usage,site=%s value=%s' % ("water", 0)
            client.publish(mqttPublishTopic, msg)

    previous_pipe_temp = data[1]


def publish():
    while True:
        try:
            checkWifi()
            sensors_data = readSensor()
            counter = 1

            for data in sensors_data:
                print(data)
                name = "temp_pipe" if data[0] == "pipe" else "temp_tank"

                msg = b'%s,site=%s value=%s' % (name, data[0], data[1])
                client.publish(mqttPublishTopic, msg)
                counter += 1

            time.sleep(messageInterval)
        except OSError:
            restartAndReconnect()


esp.osdebug(None)
gc.collect()

dsPin = machine.Pin(4)
dsSensor = ds18x20.DS18X20(onewire.OneWire(dsPin))
client = MQTTClient(clientID, mqttServerIP)

try:
    connectMQTT()
except OSError as e:
    restartAndReconnect()

publish()
