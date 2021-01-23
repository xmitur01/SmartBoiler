import network

ssid = 'XIXAO'  # change to Your Wi_fi ID
password = 'Jack5528'   # change to Your Wi_fi password

station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while not station.isconnected():
    pass

print('Connection successful')
print(station.ifconfig())
