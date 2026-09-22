import tkinter as tk
from netmiko import ConnectHandler
from tkinter import messagebox
from getpass import getpass


connection = None


def connect_to_switch():
    global connection

    switch = {
        "device_type": "juniper_junos",
        "host": "192.168.1.1",
        "username": "admin",
        "password": getpass("Enter switch password: ")
    }

    try:
        connection = ConnectHandler(**switch)

        output.delete("1.0", tk.END)
        output.insert(tk.END, "Connected to switch!\n")

    except Exception as error:
        connection = None
        messagebox.showerror("Connection Error", str(error))


def show_version():
    if connection is None:
        messagebox.showwarning(
            "Not Connected",
            "Please connect to the switch first."
        )
        return

    try:
        result = connection.send_command("show version")

        output.delete("1.0", tk.END)
        output.insert(tk.END, result)

    except Exception as error:
        messagebox.showerror("Command Error", str(error))


window = tk.Tk()
window.title("Juniper Switch Control")
window.geometry("700x500")


title = tk.Label(
    window,
    text="Juniper Switch Control",
    font=("Arial", 20)
)

title.pack(pady=20)


connect_button = tk.Button(
    window,
    text="Connect to Switch",
    width=20,
    command=connect_to_switch
)

connect_button.pack(pady=5)


version_button = tk.Button(
    window,
    text="Show Version",
    width=20,
    command=show_version
)

version_button.pack(pady=5)


output = tk.Text(
    window,
    width=80,
    height=20
)

output.pack(pady=20)


window.mainloop()