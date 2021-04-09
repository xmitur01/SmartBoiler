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
# KEY_TYPE = input("Enter network key type, from scan result: ")

plug.wifi_join(SSID, PASSWORD)
plug.erase_emeter_stats()
