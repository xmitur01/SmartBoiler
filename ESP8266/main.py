"""
Implementation of NodeMCU ESP 8266 automata for monitoring temperature data.

author: J.Mitura (xmitur01)
version: 1.0
"""
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
mqttServerIP = '192.168.1.105'  # change to Your MQTT server IP

lastMessage = 0
messageInterval = 5


def connectMQTT():
    """Make connection with MQTT server and print message on serial output for debug."""
    client.reconnect()
    print("Connected to %s MQTT broker" % mqttServerIP)


def restartAndReconnect():
    """Restarts machine when connection to server is unsuccessful. Print message for debug."""
    print("Restarting and reconnecting.")
    time.sleep(10)
    machine.reset()


def checkWifi():
    """Checking Wi-Fi connection.
    If connection is lost then loops till connection is up again and reconnects to MQTT server.
    """
    connection_lost = False

    while not boot.station.isconnected():
        time.sleep_ms(500)
        connection_lost = True
        boot.station.connect()

    if connection_lost:
        client.reconnect()


def decodeByteArray(byte_arr):
    """Based on sensor address return name of sensor. Variable value need to be set on specific address of pipe sensor.

    :param byte_arr: byte array with unique sensor address
    :return: string with name of temperature sensor based on location
    """
    value = unpack('<H', byte_arr)[0]
    if value == 32040:
        return "pipe"
    else:
        return "tank"


def readSensor():
    """Read temperatures form sensors, reformat their values to xxx.x number notation and save it to list with names.
    In case of sensor read error empty list return. In case of system error device restarts.

    :return: list of lists[string=name, string=temperature] or empty list []
    """
    try:
        roms = ds_sensor.scan()
        ds_sensor.convert_temp()
        time.sleep_ms(750)
        sensors_temperatures = []

        for rom in roms:
            sensor_temp = ds_sensor.read_temp(rom)

            if isinstance(sensor_temp, float) or (isinstance(sensor_temp, int)):
                reformat_temp = ('{0:3.1f}'.format(sensor_temp))
                sensors_temperatures.append([decodeByteArray(byte_arr=rom), reformat_temp])
            else:
                print("Invalid sensor readings format.")
                return []

        return sensors_temperatures
    except OSError:
        print("Failed to read sensor.")
        restartAndReconnect()


def publish():
    """In 5 second intervals run main automata cycle(check connection, read sensor data, publish via MQTT).
    Tries to publish sensor data, if error occurs restart machine and reconnect.
    """
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


# ===================================== #
#                 MAIN                  #
# ===================================== #

esp.osdebug(None)
gc.collect()

ds_pin = machine.Pin(4)     # GPIO pin with sensors connected
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))    # initialize for communication via one wire protocol
client = MQTTClient(clientID, mqttServerIP)

# Try to create connection with MQTT server
try:
    connectMQTT()
except OSError as e:
    restartAndReconnect()

publish()
