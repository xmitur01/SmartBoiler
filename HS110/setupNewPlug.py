"""
Script for Tp-Link HS110 smart plug setup.
Run after connecting to plug Wi-Fi network.

author: J.Mitura (xmitur01)
version: 1.0
"""
import kasa


print("----PLUG SET UP-----"
      "\n")
print("Scanning network for devices...")

devices = kasa.discover
print(devices)

plugAddress = input("Enter smart plug ip: ")
plug = kasa.SmartPlug(plugAddress)

plug.wifi_scan()

SSID = input("Enter your network SSID: ")
PASSWORD = input("Enter PASSWORD to your network: ")

plug.erase_emeter_stats()
plug.wifi_join(SSID, PASSWORD)
