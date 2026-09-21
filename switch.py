from netmiko import ConnectHandler

switch = {
    "device_type": "juniper_junos",
    "host": "192.168.10.1",
    "username": "nour",
    "password": "YOUR_PASSWORD"
}

connection = ConnectHandler(**switch)

print("Connected!")

connection.disconnect()