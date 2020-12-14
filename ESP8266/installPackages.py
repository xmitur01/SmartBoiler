import network
import upip

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("SSID", "PASSWORD")

upip.install('micropython-umqtt.simple')
upip.install('micropython-umqtt.robust')
