import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from netmiko import ConnectHandler


# ============================================================
# Switch Database
# ============================================================

switches = [
    {
        "ip": "192.168.1.1"
    },

    {
        "ip": "192.168.1.2"
    },

    # Add more switches later:
    #
    # {
    #     "ip": "192.168.1.3"
    # }
]


# ============================================================
# Global Connection
# ============================================================

connection = None
current_switch = None


# ============================================================
# Generate Switch Name
# ============================================================

def generate_switch_name(ip):

    prefix = prefix_entry.get().strip()

    if prefix == "":
        prefix = "switch-"

    last_part = ip.split(".")[-1]

    return prefix + last_part


# ============================================================
# Get Selected Switch
# ============================================================

def get_selected_switch():

    selected = switch_combo.get()

    if selected == "":
        return None

    for switch in switches:

        switch_name = generate_switch_name(
            switch["ip"]
        )

        if selected == switch_name:
            return switch

    return None


# ============================================================
# Update Switch Names in ComboBox
# ============================================================

def update_switch_names():

    names = []

    for switch in switches:

        name = generate_switch_name(
            switch["ip"]
        )

        names.append(name)

    switch_combo["values"] = names

    # Reset selection
    switch_combo.set("")

    disconnect_from_switch()


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
# Clear Dashboard
# ============================================================

def clear_dashboard():

    dashboard_hostname.config(
        text="Hostname: -"
    )

    dashboard_ip.config(
        text="IP Address: -"
    )

    dashboard_status.config(
        text="Status: No switch selected"
    )

    dashboard_model.config(
        text="Model: -"
    )

    dashboard_junos.config(
        text="Junos Version: -"
    )

    dashboard_uptime.config(
        text="Uptime: -"
    )


# ============================================================
# Update Dashboard
# ============================================================

def update_dashboard():

    if connection is None or current_switch is None:
        clear_dashboard()
        return

    hostname = generate_switch_name(
        current_switch["ip"]
    )

    ip = current_switch["ip"]

    try:

        version_output = connection.send_command(
            "show version"
        )

        uptime_output = connection.send_command(
            "show system uptime"
        )

        # ----------------------------------------------------
        # Find Junos Version
        # ----------------------------------------------------

        junos_version = "-"

        for line in version_output.splitlines():

            if "Junos:" in line:

                junos_version = line.split(
                    "Junos:", 1
                )[1].strip()

                break

        # ----------------------------------------------------
        # Find Model
        # ----------------------------------------------------

        model = "-"

        for line in version_output.splitlines():

            if "Model:" in line:

                model = line.split(
                    "Model:", 1
                )[1].strip()

                break

        # ----------------------------------------------------
        # Find Uptime
        # ----------------------------------------------------

        uptime = "-"

        for line in uptime_output.splitlines():

            if "System booted:" in line:

                uptime = line.strip()

                break

            if "System uptime:" in line:

                uptime = line.strip()

                break

        # ----------------------------------------------------
        # Update Dashboard
        # ----------------------------------------------------

        dashboard_hostname.config(
            text=f"Hostname: {hostname}"
        )

        dashboard_ip.config(
            text=f"IP Address: {ip}"
        )

        dashboard_status.config(
            text="Status: Connected"
        )

        dashboard_model.config(
            text=f"Model: {model}"
        )

        dashboard_junos.config(
            text=f"Junos Version: {junos_version}"
        )

        dashboard_uptime.config(
            text=f"Uptime: {uptime}"
        )

    except Exception as error:

        print(
            f"Dashboard error: {error}"
        )

        dashboard_status.config(
            text="Status: Connected"
        )

        dashboard_model.config(
            text="Model: Unable to retrieve"
        )

        dashboard_junos.config(
            text="Junos Version: Unable to retrieve"
        )

        dashboard_uptime.config(
            text="Uptime: Unable to retrieve"
        )


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

    # Reset ComboBox selection
    switch_combo.set("")

    status_label.config(
        text="Status: No switch selected"
    )

    clear_dashboard()

    output.delete(
        "1.0",
        tk.END
    )

    output.insert(
        tk.END,
        "No switch selected.\n"
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

        return

    hostname = generate_switch_name(
        selected_switch["ip"]
    )

    ip = selected_switch["ip"]

    # --------------------------------------------------------
    # Disconnect Previous Switch
    # --------------------------------------------------------

    if connection is not None:

        try:
            connection.disconnect()

        except Exception:
            pass

        connection = None
        current_switch = None

        disable_command_buttons()
        clear_dashboard()

    # --------------------------------------------------------
    # Show Connecting Status
    # --------------------------------------------------------

    status_label.config(
        text=f"Status: Connecting to {hostname}..."
    )

    dashboard_hostname.config(
        text=f"Hostname: {hostname}"
    )

    dashboard_ip.config(
        text=f"IP Address: {ip}"
    )

    dashboard_status.config(
        text="Status: Connecting..."
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

        status_label.config(
            text=f"Status: Connected to {hostname}"
        )

        enable_command_buttons()

        update_dashboard()

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
        clear_dashboard()

        status_label.config(
            text="Status: Connection failed"
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
# Generate Password
# ============================================================

def generate_password(ip):

    last_part = ip.split(".")[-1]

    return "switch-" + last_part


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

    # Ask user for number of lines
    lines = simpledialog.askinteger(
        "Show Logs",
        "How many log lines do you want to display?",
        parent=window,
        minvalue=1
    )

    # User pressed Cancel
    if lines is None:
        return

    try:

        result = connection.send_command(
            f"show log messages | last {lines}"
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

    hostname = generate_switch_name(
        current_switch["ip"]
    )

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

    if selected_switch is None:

        disconnect_from_switch()

        return

    connect_to_selected_switch()


# ============================================================
# Main Window
# ============================================================

window = tk.Tk()

window.title(
    "Juniper Switch Control"
)

window.geometry(
    "900x850"
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
# Switch Prefix
# ============================================================

prefix_frame = tk.Frame(
    window
)

prefix_frame.pack(
    pady=5
)


prefix_label = tk.Label(
    prefix_frame,
    text="Switch Prefix:",
    font=("Arial", 11)
)

prefix_label.pack(
    side="left",
    padx=5
)


prefix_entry = tk.Entry(
    prefix_frame,
    width=20
)

prefix_entry.insert(
    0,
    "switch-"
)

prefix_entry.pack(
    side="left",
    padx=5
)


update_names_button = tk.Button(
    prefix_frame,
    text="Apply Prefix",
    command=update_switch_names
)

update_names_button.pack(
    side="left",
    padx=5
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
    generate_switch_name(
        switch["ip"]
    )
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
# Switch Dashboard
# ============================================================

dashboard_frame = tk.LabelFrame(
    window,
    text="Switch Dashboard",
    padx=15,
    pady=10
)

dashboard_frame.pack(
    fill="x",
    padx=20,
    pady=10
)


dashboard_hostname = tk.Label(
    dashboard_frame,
    text="Hostname: -",
    anchor="w",
    font=("Arial", 10)
)

dashboard_hostname.pack(
    fill="x"
)


dashboard_ip = tk.Label(
    dashboard_frame,
    text="IP Address: -",
    anchor="w",
    font=("Arial", 10)
)

dashboard_ip.pack(
    fill="x"
)


dashboard_status = tk.Label(
    dashboard_frame,
    text="Status: No switch selected",
    anchor="w",
    font=("Arial", 10)
)

dashboard_status.pack(
    fill="x"
)


dashboard_model = tk.Label(
    dashboard_frame,
    text="Model: -",
    anchor="w",
    font=("Arial", 10)
)

dashboard_model.pack(
    fill="x"
)


dashboard_junos = tk.Label(
    dashboard_frame,
    text="Junos Version: -",
    anchor="w",
    font=("Arial", 10)
)

dashboard_junos.pack(
    fill="x"
)


dashboard_uptime = tk.Label(
    dashboard_frame,
    text="Uptime: -",
    anchor="w",
    font=("Arial", 10)
)

dashboard_uptime.pack(
    fill="x"
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
    height=15
)

output.pack(
    pady=5
)


# ============================================================
# Start GUI
# ============================================================

window.mainloop()