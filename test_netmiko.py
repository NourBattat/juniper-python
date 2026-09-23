from netmiko import ConnectHandler
from getpass import getpass


username = input("Username: ")
password = getpass("Password: ")


switch = {
    "device_type": "juniper_junos",
    "host": "192.168.1.1",
    "username": username,
    "password": password,
    "allow_agent": False
}


try:
    print("Connecting...")

    connection = ConnectHandler(**switch)

    print("CONNECTED!")

    output = connection.send_command("show version")

    print(output)

    connection.disconnect()

    print("Disconnected.")

except Exception as error:

    print("CONNECTION FAILED")
    print(error)