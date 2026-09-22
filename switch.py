from netmiko import ConnectHandler

switch = {
    "device_type": "juniper_junos",
    "host": "192.168.1.1",
    "username": "admin",
    "password": password
}

connection = ConnectHandler(**switch)

print("Connected!")

output = connection.send_command("show version")

print(output)

connection.disconnect()