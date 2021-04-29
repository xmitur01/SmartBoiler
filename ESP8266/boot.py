"""
Implementation of NodeMCU ESP 8266 boot sequence.
Provides Wi-Fi connection.

author: J.Mitura (xmitur01)
version: 1.0
"""
import network

ssid = 'SSID'  # change to Your Wi_fi ID
password = 'PASSWORD'   # change to Your Wi_fi password

station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while not station.isconnected():
    pass

print('Connection successful')
print(station.ifconfig())
