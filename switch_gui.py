import tkinter as tk
from tkinter import messagebox
from netmiko import ConnectHandler


# Store the SSH connection
connection = None


# =========================
# Connect to Switch
# =========================

def connect_to_switch():
    global connection

    username = username_entry.get()
    password = password_entry.get()

    # Check username
    if username == "":
        messagebox.showwarning(
            "Missing Username",
            "Please enter a username."
        )
        return

    # Check password
    if password == "":
        messagebox.showwarning(
            "Missing Password",
            "Please enter a password."
        )
        return

    switch = {
        "device_type": "juniper_junos",
        "host": "192.168.1.1",
        "username": username,
        "password": password,

        # Disable SSH agent authentication
        "allow_agent": False
    }

    try:
        # Connect to the switch
        connection = ConnectHandler(**switch)

        # Update status
        status_label.config(
            text="Status: Connected"
        )

        # Clear output
        output.delete(
            "1.0",
            tk.END
        )

        # Show connection message
        output.insert(
            tk.END,
            "Connected to switch!\n\n"
        )

        # Enable command buttons
        version_button.config(
            state="normal"
        )

        interfaces_button.config(
            state="normal"
        )

        vlans_button.config(
            state="normal"
        )

    except Exception as error:

        # Connection failed
        connection = None

        status_label.config(
            text="Status: Connection failed"
        )

        # Disable command buttons
        version_button.config(
            state="disabled"
        )

        interfaces_button.config(
            state="disabled"
        )

        vlans_button.config(
            state="disabled"
        )

        messagebox.showerror(
            "Connection Error",
            "Could not connect to the switch.\n\n"
            + str(error)
        )


# =========================
# Show Version
# =========================

def show_version():

    if connection is None:
        return

    try:

        result = connection.send_command(
            "show version"
        )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            result
        )

    except Exception as error:

        messagebox.showerror(
            "Command Error",
            str(error)
        )


# =========================
# Show Interfaces
# =========================

def show_interfaces():

    if connection is None:
        return

    try:

        result = connection.send_command(
            "show interfaces terse"
        )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            result
        )

    except Exception as error:

        messagebox.showerror(
            "Command Error",
            str(error)
        )


# =========================
# Show VLANs
# =========================

def show_vlans():

    if connection is None:
        return

    try:

        result = connection.send_command(
            "show vlans"
        )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            result
        )

    except Exception as error:

        messagebox.showerror(
            "Command Error",
            str(error)
        )


# =========================
# Disconnect
# =========================

def disconnect_from_switch():
    global connection

    if connection is not None:

        try:
            connection.disconnect()
        except:
            pass

        connection = None

    # Update status
    status_label.config(
        text="Status: Not connected"
    )

    # Disable buttons
    version_button.config(
        state="disabled"
    )

    interfaces_button.config(
        state="disabled"
    )

    vlans_button.config(
        state="disabled"
    )

    # Clear output
    output.delete(
        "1.0",
        tk.END
    )

    output.insert(
        tk.END,
        "Disconnected from switch.\n"
    )


# =========================
# Create Window
# =========================

window = tk.Tk()

window.title(
    "Juniper Switch Control"
)

window.geometry(
    "750x700"
)


# =========================
# Title
# =========================

title = tk.Label(
    window,
    text="Juniper Switch Control",
    font=("Arial", 20)
)

title.pack(
    pady=15
)


# =========================
# Username
# =========================

username_label = tk.Label(
    window,
    text="Username:"
)

username_label.pack()


username_entry = tk.Entry(
    window,
    width=30
)

username_entry.insert(
    0,
    "admin"
)

username_entry.pack(
    pady=5
)


# =========================
# Password
# =========================

password_label = tk.Label(
    window,
    text="Password:"
)

password_label.pack()


password_entry = tk.Entry(
    window,
    width=30,
    show="*"
)

password_entry.pack(
    pady=5
)


# =========================
# Connect Button
# =========================

connect_button = tk.Button(
    window,
    text="Connect to Switch",
    width=20,
    command=connect_to_switch
)

connect_button.pack(
    pady=10
)


# =========================
# Disconnect Button
# =========================

disconnect_button = tk.Button(
    window,
    text="Disconnect",
    width=20,
    command=disconnect_from_switch
)

disconnect_button.pack(
    pady=5
)


# =========================
# Status
# =========================

status_label = tk.Label(
    window,
    text="Status: Not connected",
    font=("Arial", 11)
)

status_label.pack(
    pady=10
)


# =========================
# Show Version Button
# =========================

version_button = tk.Button(
    window,
    text="Show Version",
    width=20,
    command=show_version,
    state="disabled"
)

version_button.pack(
    pady=5
)


# =========================
# Show Interfaces Button
# =========================

interfaces_button = tk.Button(
    window,
    text="Show Interfaces",
    width=20,
    command=show_interfaces,
    state="disabled"
)

interfaces_button.pack(
    pady=5
)


# =========================
# Show VLANs Button
# =========================

vlans_button = tk.Button(
    window,
    text="Show VLANs",
    width=20,
    command=show_vlans,
    state="disabled"
)

vlans_button.pack(
    pady=5
)


# =========================
# Output Box
# =========================

output = tk.Text(
    window,
    width=85,
    height=22
)

output.pack(
    pady=15
)


# =========================
# Start GUI
# =========================

window.mainloop()