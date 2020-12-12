try:
    import usocket as socket
finally:
    import socket

from time import sleep
from machine import Pin
import onewire
import ds18x20
import network
import esp
import gc

esp.osdebug(None)
gc.collect()

ds_pin = Pin(4)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

ssid = 'XIXAO'
password = 'Jack5528'

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)

while station.isconnected() == False:
    pass

print('Connection successful')
print(station.ifconfig())
