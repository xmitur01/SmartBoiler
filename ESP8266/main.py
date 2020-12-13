import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
from machine import Pin
import onewire
import ds18x20
import gc

esp.osdebug(None)
gc.collect()

ssid = 'XIXAO'
password = 'Jack5528'
mqtt_server = '192.168.1.105'

topic_pub_temp = b'sensors'
client_id = ubinascii.hexlify(machine.unique_id())

last_message = 0
message_interval = 5

ds_pin = machine.Pin(4)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))


def connect_to_wifi():
    station = network.WLAN(network.STA_IF)

    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        pass

    print('Connection successful')


def connect_mqtt():
    global client_id, mqtt_server
    mqtt_client = MQTTClient(client_id, mqtt_server)
    # mqtt_client = MQTTClient(client_id, mqtt_server, user=your_username, password=your_password)
    mqtt_client.connect()
    print('Connected to %s MQTT broker' % mqtt_server)
    return mqtt_client


def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    time.sleep(10)
    machine.reset()


def read_sensor():  # TODO
    try:
        roms = ds_sensor.scan()
        ds_sensor.convert_temp()
        time.sleep_ms(750)

        for rom in roms:
            sensor_temp = ds_sensor.read_temp(rom)

        if (isinstance(sensor_temp, float) or (isinstance(sensor_temp, int))):
            sensor_temp = (b'{0:3.1f},'.format(sensor_temp))
            return sensor_temp
        else:
            return 'Invalid sensor readings.'
    except OSError:
        return 'Failed to read sensor.'


connect_to_wifi()
try:
    client = connect_mqtt()
except OSError as e:
    restart_and_reconnect()

while True:
    try:
        if (time.time() - last_message) > message_interval:
            temp = read_sensor()
            print(temp)
            client.publish(topic_pub_temp, temp)
            last_message = time.time()
    except OSError as e:
        restart_and_reconnect()

# import machine
# import onewire
# import ds18x20
# import time
#
#

# mqtt_server = '192.168.1.105'
#
# client_id = ubinascii.hexlify(machine.unique_id())
# topic_pub = b'sensors'
#
# last_message = 0
# message_interval = 5
# counter = 0
#
# ds_pin = machine.Pin(4)
# ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
#
# roms = ds_sensor.scan()
# print('Found DS devices: ', roms, '\n')
#
# while True:
#     ds_sensor.convert_temp()
#     time.sleep_ms(750)
#     for rom in roms:
#         print(rom)
#         print(str(ds_sensor.read_temp(rom)) + " °C")
#         print()
#     time.sleep(5)
