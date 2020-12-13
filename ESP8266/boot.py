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
esp.osdebug(None)
import gc
gc.collect()

esp.osdebug(None)
gc.collect()

ssid = 'XIXAO'
password = 'Jack5528'

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)

while not station.isconnected():
    pass

print('Connection successful')
print(station.ifconfig())
