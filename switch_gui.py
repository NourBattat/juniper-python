import tkinter as tk
from tkinter import ttk, messagebox
from netmiko import ConnectHandler


# ============================================================
# Switch Database
# ============================================================

switches = [
    {
        "hostname": "switch-1",
        "ip": "192.168.1.1"
    },

    {
        "hostname": "switch-2",
        "ip": "192.168.1.2"
    },

    # Add more switches later:
    #
    # {
    #     "hostname": "switch-3",
    #     "ip": "192.168.1.3"
    # }
]


# ============================================================
# Global Connection
# ============================================================

connection = None

current_switch = None


# ============================================================
# Generate Password
# ============================================================

def generate_password(ip):

    last_part = ip.split(".")[-1]

    return "switch-" + last_part


# ============================================================
# Get Selected Switch
# ============================================================

def get_selected_switch():

    selected = switch_combo.get()

    if selected == "":
        return None

    for switch in switches:

        if selected == switch["hostname"]:
            return switch

    return None


# ============================================================
# Enable Command Buttons
# ============================================================

def enable_command_buttons():

    version_button.config(state="normal")
    interfaces_button.config(state="normal")
    vlans_button.config(state="normal")
    logs_button.config(state="normal")
    restart_button.config(state="normal")
    run_command_button.config(state="normal")


# ============================================================
# Disable Command Buttons
# ============================================================

def disable_command_buttons():

    version_button.config(state="disabled")
    interfaces_button.config(state="disabled")
    vlans_button.config(state="disabled")
    logs_button.config(state="disabled")
    restart_button.config(state="disabled")
    run_command_button.config(state="disabled")


# ============================================================
# Disconnect Current Switch
# ============================================================

def disconnect_from_switch():

    global connection
    global current_switch

    if connection is not None:

        try:
            connection.disconnect()

        except Exception:
            pass

    connection = None
    current_switch = None

    disable_command_buttons()

    status_label.config(
        text="Status: Not connected"
    )


# ============================================================
# Connect Automatically to Selected Switch
# ============================================================

def connect_to_selected_switch():

    global connection
    global current_switch

    selected_switch = get_selected_switch()

    # --------------------------------------------------------
    # No switch selected
    # --------------------------------------------------------

    if selected_switch is None:

        disconnect_from_switch()

        status_label.config(
            text="Status: No switch selected"
        )

        return

    hostname = selected_switch["hostname"]
    ip = selected_switch["ip"]

    # --------------------------------------------------------
    # Disconnect from previous switch first
    # --------------------------------------------------------

    if connection is not None:

        try:
            connection.disconnect()

        except Exception:
            pass

        connection = None
        current_switch = None

        disable_command_buttons()

    # --------------------------------------------------------
    # Show connecting status
    # --------------------------------------------------------

    status_label.config(
        text=f"Status: Connecting to {hostname}..."
    )

    output.delete(
        "1.0",
        tk.END
    )

    output.insert(
        tk.END,
        f"Connecting to {hostname}...\n"
        f"IP Address: {ip}\n"
    )

    window.update()

    # --------------------------------------------------------
    # Credentials
    # --------------------------------------------------------

    username = "admin"
    password = generate_password(ip)

    switch = {
        "device_type": "juniper_junos",
        "host": ip,
        "username": username,
        "password": password,
        "allow_agent": False
    }

    # --------------------------------------------------------
    # Connect
    # --------------------------------------------------------

    try:

        connection = ConnectHandler(**switch)

        current_switch = selected_switch

        # Status
        status_label.config(
            text=f"Status: Connected to {hostname}"
        )

        # Enable commands
        enable_command_buttons()

        # Output
        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            f"Connected successfully!\n\n"
            f"Hostname: {hostname}\n"
            f"IP Address: {ip}\n"
        )

    except Exception as error:

        connection = None
        current_switch = None

        disable_command_buttons()

        status_label.config(
            text=f"Status: Connection failed"
        )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            f"Could not connect to {hostname}\n\n"
            f"IP Address: {ip}\n\n"
            f"Error:\n{error}"
        )

        messagebox.showerror(
            "Connection Error",
            f"Could not connect to {hostname}.\n\n"
            + str(error)
        )


# ============================================================
# Show Version
# ============================================================

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


# ============================================================
# Show Interfaces
# ============================================================

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


# ============================================================
# Show VLANs
# ============================================================

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


# ============================================================
# Show Logs
# ============================================================

def show_logs():

    if connection is None:
        return

    try:

        result = connection.send_command(
            "show log messages"
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


# ============================================================
# Restart Switch
# ============================================================

def restart_switch():

    if connection is None:
        return

    if current_switch is None:
        return

    hostname = current_switch["hostname"]

    confirmation = messagebox.askyesno(
        "Restart Switch",
        f"Are you sure you want to restart {hostname}?\n\n"
        "The switch will temporarily go offline."
    )

    if not confirmation:
        return

    try:

        result = connection.send_command_timing(
            "request system reboot"
        )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            result
        )

        messagebox.showinfo(
            "Restart",
            f"{hostname} is restarting."
        )

        disconnect_from_switch()

    except Exception as error:

        messagebox.showerror(
            "Restart Error",
            str(error)
        )


# ============================================================
# Run Custom Command
# ============================================================

def run_custom_command():

    if connection is None:
        return

    command = command_entry.get().strip()

    if command == "":

        messagebox.showwarning(
            "Missing Command",
            "Please enter a Junos command."
        )

        return

    try:

        result = connection.send_command(
            command
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


# ============================================================
# When User Selects Another Switch
# ============================================================

def switch_selected(event=None):

    selected_switch = get_selected_switch()

    # --------------------------------------------------------
    # Nothing selected
    # --------------------------------------------------------

    if selected_switch is None:

        disconnect_from_switch()

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            "No switch selected.\n"
        )

        return

    # --------------------------------------------------------
    # Automatically connect
    # --------------------------------------------------------

    connect_to_selected_switch()


# ============================================================
# Main Window
# ============================================================

window = tk.Tk()

window.title(
    "Juniper Switch Control"
)

window.geometry(
    "900x750"
)


# ============================================================
# Title
# ============================================================

title = tk.Label(
    window,
    text="Juniper Switch Control",
    font=("Arial", 22)
)

title.pack(
    pady=15
)


# ============================================================
# Switch Selection
# ============================================================

selection_frame = tk.Frame(
    window
)

selection_frame.pack(
    pady=10
)


select_label = tk.Label(
    selection_frame,
    text="Select Switch:",
    font=("Arial", 11)
)

select_label.pack(
    side="left",
    padx=5
)


switch_combo = ttk.Combobox(
    selection_frame,
    width=30,
    state="readonly"
)

switch_combo["values"] = [
    switch["hostname"]
    for switch in switches
]

switch_combo.pack(
    side="left",
    padx=5
)

switch_combo.bind(
    "<<ComboboxSelected>>",
    switch_selected
)


# ============================================================
# IMPORTANT:
# Do NOT select a switch automatically.
#
# There is NO:
#
# switch_combo.current(0)
#
# ============================================================


# ============================================================
# Disconnect Button
# ============================================================

disconnect_button = tk.Button(
    window,
    text="Disconnect",
    width=22,
    command=disconnect_from_switch
)

disconnect_button.pack(
    pady=8
)


# ============================================================
# Status
# ============================================================

status_label = tk.Label(
    window,
    text="Status: No switch selected",
    font=("Arial", 11)
)

status_label.pack(
    pady=8
)


# ============================================================
# Basic Commands Frame
# ============================================================

commands_frame = tk.Frame(
    window
)

commands_frame.pack(
    pady=5
)


# ============================================================
# Show Version
# ============================================================

version_button = tk.Button(
    commands_frame,
    text="Show Version",
    width=18,
    command=show_version,
    state="disabled"
)

version_button.grid(
    row=0,
    column=0,
    padx=5,
    pady=5
)


# ============================================================
# Show Interfaces
# ============================================================

interfaces_button = tk.Button(
    commands_frame,
    text="Show Interfaces",
    width=18,
    command=show_interfaces,
    state="disabled"
)

interfaces_button.grid(
    row=0,
    column=1,
    padx=5,
    pady=5
)


# ============================================================
# Show VLANs
# ============================================================

vlans_button = tk.Button(
    commands_frame,
    text="Show VLANs",
    width=18,
    command=show_vlans,
    state="disabled"
)

vlans_button.grid(
    row=0,
    column=2,
    padx=5,
    pady=5
)


# ============================================================
# Show Logs
# ============================================================

logs_button = tk.Button(
    commands_frame,
    text="Show Logs",
    width=18,
    command=show_logs,
    state="disabled"
)

logs_button.grid(
    row=0,
    column=3,
    padx=5,
    pady=5
)


# ============================================================
# Restart
# ============================================================

restart_button = tk.Button(
    commands_frame,
    text="Restart Switch",
    width=18,
    command=restart_switch,
    state="disabled"
)

restart_button.grid(
    row=1,
    column=0,
    columnspan=4,
    pady=8
)


# ============================================================
# Custom Command
# ============================================================

command_label = tk.Label(
    window,
    text="Custom Junos Command:",
    font=("Arial", 11)
)

command_label.pack(
    pady=(10, 5)
)


command_entry = tk.Entry(
    window,
    width=65
)

command_entry.pack(
    pady=5
)


run_command_button = tk.Button(
    window,
    text="Run Command",
    width=22,
    command=run_custom_command,
    state="disabled"
)

run_command_button.pack(
    pady=5
)


# ============================================================
# Output
# ============================================================

output_label = tk.Label(
    window,
    text="Command Output:",
    font=("Arial", 11)
)

output_label.pack(
    pady=(10, 5)
)


output = tk.Text(
    window,
    width=105,
    height=20
)

output.pack(
    pady=5
)


# ============================================================
# Start GUI
# ============================================================

window.mainloop()