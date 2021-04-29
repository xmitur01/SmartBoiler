"""
Script for installing required packages on NodeMCU ESP8266.
Run after flushing microPython interpret.

author: J.Mitura (xmitur01)
version: 1.0
"""
import network
import upip

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("SSID", "PASSWORD")    # Change to Your Wi-Fi SSID and Password before running

upip.install('micropython-umqtt.simple')
upip.install('micropython-umqtt.robust')
