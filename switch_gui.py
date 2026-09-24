import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from netmiko import ConnectHandler
import json
import os
import re
from datetime import datetime


# ============================================================
# Switch Database
# ============================================================

switches = [
    {
        "hostname": "switch-1",
        "ip": "192.168.1.1",
        "password": "switch-1"
    },

    {
        "hostname": "switch-2",
        "ip": "192.168.1.2",
        "password": "switch-2"
    },
]


# ============================================================
# Database Files
# ============================================================

PASSWORD_DATABASE_FILE = "switch_passwords.json"
LOGIN_PROFILE_DATABASE_FILE = "login_profiles.json"


# ============================================================
# Login Profile
# ============================================================

active_login_profile = None


# ============================================================
# Load Password Database
# ============================================================

def load_password_database():

    if not os.path.exists(PASSWORD_DATABASE_FILE):
        return

    try:

        with open(
            PASSWORD_DATABASE_FILE,
            "r"
        ) as file:

            saved_passwords = json.load(file)

        for switch in switches:

            hostname = switch["hostname"]

            if hostname in saved_passwords:

                switch["password"] = (
                    saved_passwords[hostname]
                )

    except Exception as error:

        print(
            f"Could not load password database: {error}"
        )


# ============================================================
# Save Password Database
# ============================================================

def save_password_database():

    passwords = {}

    for switch in switches:

        passwords[switch["hostname"]] = (
            switch["password"]
        )

    try:

        with open(
            PASSWORD_DATABASE_FILE,
            "w"
        ) as file:

            json.dump(
                passwords,
                file,
                indent=4
            )

    except Exception as error:

        messagebox.showerror(
            "Database Error",
            "Could not save password database.\n\n"
            + str(error)
        )


# ============================================================
# Load Login Profile Database
# ============================================================

def load_login_profiles():

    if not os.path.exists(
        LOGIN_PROFILE_DATABASE_FILE
    ):

        return {}

    try:

        with open(
            LOGIN_PROFILE_DATABASE_FILE,
            "r"
        ) as file:

            profiles = json.load(file)

        if isinstance(profiles, dict):

            return profiles

        return {}

    except Exception as error:

        print(
            f"Could not load login profiles: {error}"
        )

        return {}


# ============================================================
# Save Login Profile
# ============================================================

def save_login_profile(
    username,
    prefix
):

    try:

        profiles = load_login_profiles()

        profiles[username] = {
            "username": username,
            "prefix": prefix
        }

        with open(
            LOGIN_PROFILE_DATABASE_FILE,
            "w"
        ) as file:

            json.dump(
                profiles,
                file,
                indent=4
            )

        return True

    except Exception as error:

        messagebox.showerror(
            "Profile Database Error",
            "Could not save login profile.\n\n"
            + str(error)
        )

        return False


# ============================================================
# Load Saved Passwords
# ============================================================

load_password_database()


# ============================================================
# Global Connection
# ============================================================

connection = None
current_switch = None


# ============================================================
# Live Monitoring Settings
# ============================================================

DEFAULT_REFRESH_SECONDS = 60

refresh_seconds = DEFAULT_REFRESH_SECONDS

refresh_job = None
refresh_countdown_job = None

remaining_refresh_seconds = DEFAULT_REFRESH_SECONDS


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
# Generate Login Profile Password
# ============================================================

def generate_profile_password(
    switch,
    prefix
):

    ip = switch["ip"]

    last_octet = ip.split(".")[-1]

    return prefix + last_octet


# ============================================================
# Use Login Profile
# ============================================================

def use_login_profile():

    global active_login_profile

    username = login_username_entry.get().strip()
    prefix = login_prefix_entry.get().strip()

    if username == "":

        messagebox.showwarning(
            "Missing Username",
            "Please enter a username."
        )

        return

    if prefix == "":

        messagebox.showwarning(
            "Missing Prefix",
            "Please enter a password prefix."
        )

        return

    # --------------------------------------------------------
    # Save profile
    # --------------------------------------------------------

    if not save_login_profile(
        username,
        prefix
    ):

        return

    active_login_profile = {
        "username": username,
        "prefix": prefix
    }

    login_profile_status.config(
        text=(
            f"Login Profile: {username} "
            f"(Prefix: {prefix})"
        )
    )

    output.delete(
        "1.0",
        tk.END
    )

    output.insert(
        tk.END,
        "Login profile activated.\n\n"
        f"Username: {username}\n"
        f"Password format: {prefix}<last IP octet>\n\n"
        "The generated password will be used "
        "when connecting to a switch."
    )

    # --------------------------------------------------------
    # If already connected, reconnect using profile
    # --------------------------------------------------------

    if current_switch is not None:

        selected_switch = current_switch

        confirmation = messagebox.askyesno(
            "Reconnect",
            "The login profile has been activated.\n\n"
            "Do you want to reconnect to the current "
            "switch using this profile?"
        )

        if confirmation:

            connect_to_selected_switch()


# ============================================================
# Disable Login Profile
# ============================================================

def disable_login_profile():

    global active_login_profile

    active_login_profile = None

    login_profile_status.config(
        text="Login Profile: Disabled"
    )

    output.delete(
        "1.0",
        tk.END
    )

    output.insert(
        tk.END,
        "Login profile disabled.\n\n"
        "The application will use the switch's "
        "stored admin credentials."
    )


# ============================================================
# Change Admin Password on One Juniper Switch
# ============================================================

def change_switch_password(
    switch,
    new_password
):

    old_connection = None

    try:

        # ----------------------------------------------------
        # Connect using CURRENT admin password
        # ----------------------------------------------------

        device = {
            "device_type": "juniper_junos",
            "host": switch["ip"],
            "username": "admin",
            "password": switch["password"],
            "allow_agent": False
        }

        old_connection = ConnectHandler(
            **device
        )

        # ----------------------------------------------------
        # Enter configuration mode
        # ----------------------------------------------------

        old_connection.config_mode()

        # ----------------------------------------------------
        # Start password change
        # ----------------------------------------------------

        result = old_connection.send_command_timing(
            "set system login user admin "
            "authentication plain-text-password"
        )

        # ----------------------------------------------------
        # Check for password prompt
        # ----------------------------------------------------

        if "new password" not in result.lower():

            raise Exception(
                "Juniper did not ask for the new password.\n\n"
                + result
            )

        # ----------------------------------------------------
        # Send NEW password
        # ----------------------------------------------------

        result = old_connection.send_command_timing(
            new_password
        )

        # ----------------------------------------------------
        # Check confirmation prompt
        # ----------------------------------------------------

        if "retype new password" not in result.lower():

            raise Exception(
                "Juniper did not ask to retype the new password.\n\n"
                + result
            )

        # ----------------------------------------------------
        # Send NEW password again
        # ----------------------------------------------------

        old_connection.send_command_timing(
            new_password
        )

        # ----------------------------------------------------
        # Commit configuration
        # ----------------------------------------------------

        commit_result = old_connection.commit(
            comment="Update admin password"
        )

        # ----------------------------------------------------
        # Disconnect
        # ----------------------------------------------------

        old_connection.disconnect()

        old_connection = None

        # ----------------------------------------------------
        # Update application database
        # ----------------------------------------------------

        switch["password"] = new_password

        return True, commit_result

    except Exception as error:

        if old_connection is not None:

            try:

                old_connection.disconnect()

            except Exception:

                pass

        return False, str(error)


# ============================================================
# Update Authentication Key
# ============================================================

def update_authentication_key():

    authentication_key = (
        authentication_key_entry.get().strip()
    )

    if authentication_key == "":

        messagebox.showwarning(
            "Missing Authentication Key",
            "Please enter an authentication key."
        )

        return

    confirmation = messagebox.askyesno(
        "Change Admin Passwords",
        "This will change the admin password on ALL "
        "switches in the database.\n\n"
        "The new password will be created from:\n"
        "Authentication Key + Last IP Octet\n\n"
        "Do you want to continue?"
    )

    if not confirmation:
        return

    # --------------------------------------------------------
    # Disconnect current switch
    # --------------------------------------------------------

    if connection is not None:

        disconnect_from_switch()

    update_key_button.config(
        state="disabled"
    )

    switch_combo.config(
        state="disabled"
    )

    window.update()

    successful_switches = []
    failed_switches = []

    # --------------------------------------------------------
    # Process every switch
    # --------------------------------------------------------

    for switch in switches:

        hostname = switch["hostname"]
        ip = switch["ip"]

        last_part = ip.split(".")[-1]

        new_password = (
            authentication_key + last_part
        )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            f"Changing admin password for {hostname}...\n\n"
            f"IP Address: {ip}\n\n"
            f"Connecting using current password...\n"
        )

        status_label.config(
            text=f"Status: Updating password for {hostname}..."
        )

        window.update()

        success, result = change_switch_password(
            switch,
            new_password
        )

        if success:

            successful_switches.append(
                hostname
            )

            output.insert(
                tk.END,
                "\nPassword changed successfully.\n"
                "Junos configuration committed.\n"
                "Application database updated.\n"
            )

        else:

            failed_switches.append(
                (
                    hostname,
                    result
                )
            )

            output.insert(
                tk.END,
                "\nPassword change FAILED.\n\n"
                f"Error:\n{result}\n"
            )

        window.update()

    # --------------------------------------------------------
    # Save database
    # --------------------------------------------------------

    if successful_switches:

        save_password_database()

    # --------------------------------------------------------
    # Restore GUI
    # --------------------------------------------------------

    switch_combo.config(
        state="readonly"
    )

    update_key_button.config(
        state="normal"
    )

    status_label.config(
        text="Status: No switch selected"
    )

    clear_dashboard()

    result_message = ""

    if successful_switches:

        result_message += (
            "Successfully updated:\n\n"
        )

        for hostname in successful_switches:

            result_message += (
                f"✓ {hostname}\n"
            )

    if failed_switches:

        result_message += (
            "\nFailed:\n\n"
        )

        for hostname, error in failed_switches:

            result_message += (
                f"✗ {hostname}\n"
            )

    if not result_message:

        result_message = (
            "No switches were updated."
        )

    messagebox.showinfo(
        "Authentication Key Update",
        result_message
    )


# ============================================================
# Enable Command Buttons
# ============================================================

def enable_command_buttons():

    version_button.config(
        state="normal"
    )

    interfaces_button.config(
        state="normal"
    )

    vlans_button.config(
        state="normal"
    )

    logs_button.config(
        state="normal"
    )

    restart_button.config(
        state="normal"
    )

    run_command_button.config(
        state="normal"
    )


# ============================================================
# Disable Command Buttons
# ============================================================

def disable_command_buttons():

    version_button.config(
        state="disabled"
    )

    interfaces_button.config(
        state="disabled"
    )

    vlans_button.config(
        state="disabled"
    )

    logs_button.config(
        state="disabled"
    )

    restart_button.config(
        state="disabled"
    )

    run_command_button.config(
        state="disabled"
    )


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

    monitor_status.config(
        text="Monitoring: Stopped"
    )

    monitor_cpu_load.config(
        text="CPU Load: -"
    )

    monitor_cpu_idle.config(
        text="CPU Idle: -"
    )

    monitor_load_average.config(
        text="Load Average: -"
    )

    monitor_temperature.config(
        text="Temperature: -"
    )

    monitor_routing_engine.config(
        text="Routing Engine: -"
    )

    monitor_alarms.config(
        text="Chassis Alarms: -"
    )

    monitor_last_update.config(
        text="Last Update: -"
    )

    monitor_countdown.config(
        text="Next Refresh: -"
    )


# ============================================================
# Parse Routing Engine Information
# ============================================================

def parse_routing_engine(result):

    cpu_idle = None
    load_1 = None
    load_5 = None
    load_15 = None

    for line in result.splitlines():

        if "Idle" in line:

            match = re.search(
                r"(\d+)\s*percent",
                line,
                re.IGNORECASE
            )

            if match:

                cpu_idle = int(
                    match.group(1)
                )

                break

    for line in result.splitlines():

        lower = line.lower()

        if "load averages" in lower:

            numbers = re.findall(
                r"\d+\.\d+",
                line
            )

            if len(numbers) >= 3:

                load_1 = numbers[0]
                load_5 = numbers[1]
                load_15 = numbers[2]

                break

    return (
        cpu_idle,
        load_1,
        load_5,
        load_15
    )


# ============================================================
# Parse Temperature
# ============================================================

def parse_temperature(result):

    temperatures = []

    for line in result.splitlines():

        lower = line.lower()

        if (
            "degrees c" in lower
            or "temperature" in lower
        ):

            matches = re.findall(
                r"(-?\d+)\s*(?:degrees\s*c|celsius|c)\b",
                line,
                re.IGNORECASE
            )

            for value in matches:

                temperatures.append(
                    int(value)
                )

    if temperatures:

        return max(
            temperatures
        )

    return None


# ============================================================
# Parse Chassis Alarms
# ============================================================

def parse_alarms(result):

    alarms = []

    for line in result.splitlines():

        stripped = line.strip()

        if stripped == "":
            continue

        lower = stripped.lower()

        if (
            "no alarms currently active" in lower
            or "no alarms" in lower
        ):

            return 0

        if (
            "alarm" in lower
            and not lower.startswith("alarm")
        ):

            alarms.append(
                stripped
            )

    actual_alarm_lines = []

    for line in result.splitlines():

        stripped = line.strip()

        if stripped == "":
            continue

        if re.match(
            r"^\d+\s+",
            stripped
        ):

            actual_alarm_lines.append(
                stripped
            )

    if actual_alarm_lines:

        return len(
            actual_alarm_lines
        )

    if alarms:

        return len(
            alarms
        )

    return 0


# ============================================================
# Update Live Monitoring Dashboard
# ============================================================

def update_live_monitor():

    global remaining_refresh_seconds

    if connection is None or current_switch is None:

        monitor_countdown.config(
            text="Next Refresh: -"
        )

        return

    try:

        routing_engine_output = (
            connection.send_command(
                "show chassis routing-engine"
            )
        )

        (
            cpu_idle,
            load_1,
            load_5,
            load_15
        ) = parse_routing_engine(
            routing_engine_output
        )

        environment_output = (
            connection.send_command(
                "show chassis environment"
            )
        )

        temperature = parse_temperature(
            environment_output
        )

        alarm_output = (
            connection.send_command(
                "show chassis alarms"
            )
        )

        alarm_count = parse_alarms(
            alarm_output
        )

        if cpu_idle is not None:

            cpu_load = 100 - cpu_idle

            monitor_cpu_idle.config(
                text=f"CPU Idle: {cpu_idle}%"
            )

            monitor_cpu_load.config(
                text=f"CPU Load: {cpu_load}%"
            )

        else:

            monitor_cpu_idle.config(
                text="CPU Idle: Unable to retrieve"
            )

            monitor_cpu_load.config(
                text="CPU Load: Unable to retrieve"
            )

        if load_1 is not None:

            monitor_load_average.config(
                text=(
                    f"Load Average: "
                    f"{load_1} / {load_5} / {load_15}"
                )
            )

        else:

            monitor_load_average.config(
                text="Load Average: Unable to retrieve"
            )

        if temperature is not None:

            monitor_temperature.config(
                text=f"Temperature: {temperature}°C"
            )

        else:

            monitor_temperature.config(
                text="Temperature: Unable to retrieve"
            )

        monitor_routing_engine.config(
            text="Routing Engine: Online"
        )

        if alarm_count == 0:

            monitor_alarms.config(
                text="Chassis Alarms: 0 (Normal)"
            )

        else:

            monitor_alarms.config(
                text=f"Chassis Alarms: {alarm_count}"
            )

        current_time = datetime.now().strftime(
            "%H:%M:%S"
        )

        monitor_last_update.config(
            text=f"Last Update: {current_time}"
        )

        monitor_status.config(
            text="Monitoring: Live"
        )

        remaining_refresh_seconds = (
            refresh_seconds
        )

        update_countdown()

    except Exception as error:

        print(
            f"Live monitoring error: {error}"
        )

        monitor_status.config(
            text="Monitoring: Connection problem"
        )

        monitor_cpu_load.config(
            text="CPU Load: Unable to retrieve"
        )

        monitor_cpu_idle.config(
            text="CPU Idle: Unable to retrieve"
        )

        monitor_load_average.config(
            text="Load Average: Unable to retrieve"
        )

        monitor_temperature.config(
            text="Temperature: Unable to retrieve"
        )

        monitor_routing_engine.config(
            text="Routing Engine: Unable to retrieve"
        )

        monitor_alarms.config(
            text="Chassis Alarms: Unable to retrieve"
        )


# ============================================================
# Schedule Live Monitoring
# ============================================================

def schedule_live_monitoring():

    global refresh_job

    if refresh_job is not None:

        try:

            window.after_cancel(
                refresh_job
            )

        except Exception:

            pass

        refresh_job = None

    if connection is None:

        return

    refresh_job = window.after(
        refresh_seconds * 1000,
        run_scheduled_monitoring
    )


# ============================================================
# Scheduled Monitoring
# ============================================================

def run_scheduled_monitoring():

    global refresh_job

    refresh_job = None

    if connection is None or current_switch is None:

        return

    update_live_monitor()

    schedule_live_monitoring()


# ============================================================
# Countdown
# ============================================================

def update_countdown():

    global refresh_countdown_job
    global remaining_refresh_seconds

    if connection is None:

        monitor_countdown.config(
            text="Next Refresh: -"
        )

        return

    monitor_countdown.config(
        text=(
            f"Next Refresh: "
            f"{remaining_refresh_seconds} sec"
        )
    )

    if remaining_refresh_seconds > 0:

        remaining_refresh_seconds -= 1

        refresh_countdown_job = window.after(
            1000,
            update_countdown
        )


# ============================================================
# Stop Live Monitoring
# ============================================================

def stop_live_monitoring():

    global refresh_job
    global refresh_countdown_job

    if refresh_job is not None:

        try:

            window.after_cancel(
                refresh_job
            )

        except Exception:

            pass

        refresh_job = None

    if refresh_countdown_job is not None:

        try:

            window.after_cancel(
                refresh_countdown_job
            )

        except Exception:

            pass

        refresh_countdown_job = None

    monitor_status.config(
        text="Monitoring: Stopped"
    )

    monitor_countdown.config(
        text="Next Refresh: -"
    )


# ============================================================
# Start Live Monitoring
# ============================================================

def start_live_monitoring():

    global remaining_refresh_seconds

    stop_live_monitoring()

    remaining_refresh_seconds = (
        refresh_seconds
    )

    update_live_monitor()

    schedule_live_monitoring()


# ============================================================
# Change Refresh Interval
# ============================================================

def apply_refresh_interval():

    global refresh_seconds
    global remaining_refresh_seconds

    value = refresh_interval_entry.get().strip()

    if value == "":

        messagebox.showwarning(
            "Refresh Interval",
            "Please enter the number of seconds."
        )

        return

    try:

        seconds = int(value)

    except ValueError:

        messagebox.showwarning(
            "Refresh Interval",
            "Please enter a valid whole number."
        )

        return

    if seconds < 5:

        messagebox.showwarning(
            "Refresh Interval",
            "Please use at least 5 seconds."
        )

        return

    refresh_seconds = seconds

    remaining_refresh_seconds = (
        refresh_seconds
    )

    if connection is not None:

        start_live_monitoring()

    else:

        monitor_countdown.config(
            text=(
                f"Next Refresh: "
                f"{refresh_seconds} sec"
            )
        )

    monitor_status.config(
        text=(
            f"Monitoring interval: "
            f"{refresh_seconds} seconds"
        )
    )


# ============================================================
# Update Basic Dashboard
# ============================================================

def update_dashboard():

    if connection is None or current_switch is None:

        clear_dashboard()

        return

    hostname = current_switch["hostname"]
    ip = current_switch["ip"]

    try:

        version_output = connection.send_command(
            "show version"
        )

        uptime_output = connection.send_command(
            "show system uptime"
        )

        junos_version = "-"

        for line in version_output.splitlines():

            if "Junos:" in line:

                junos_version = line.split(
                    "Junos:", 1
                )[1].strip()

                break

        model = "-"

        for line in version_output.splitlines():

            if "Model:" in line:

                model = line.split(
                    "Model:", 1
                )[1].strip()

                break

        uptime = "-"

        for line in uptime_output.splitlines():

            if "System booted:" in line:

                uptime = line.strip()

                break

            if "System uptime:" in line:

                uptime = line.strip()

                break

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

    stop_live_monitoring()

    if connection is not None:

        try:

            connection.disconnect()

        except Exception:

            pass

    connection = None
    current_switch = None

    disable_command_buttons()

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

    if selected_switch is None:

        disconnect_from_switch()

        return

    hostname = selected_switch["hostname"]
    ip = selected_switch["ip"]

    # --------------------------------------------------------
    # Stop previous monitoring
    # --------------------------------------------------------

    stop_live_monitoring()

    # --------------------------------------------------------
    # Disconnect previous connection
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
    # Show connecting status
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
        f"IP Address: {ip}\n\n"
    )

    window.update()

    # ========================================================
    # Determine Credentials
    # ========================================================

    if active_login_profile is not None:

        username = active_login_profile["username"]

        prefix = active_login_profile["prefix"]

        password = generate_profile_password(
            selected_switch,
            prefix
        )

        credential_mode = "Login Profile"

    else:

        username = "admin"

        password = selected_switch["password"]

        credential_mode = "Stored Admin Credentials"

    # --------------------------------------------------------
    # Do NOT display generated password
    # --------------------------------------------------------

    output.insert(
        tk.END,
        f"Credential Mode: {credential_mode}\n"
        f"Username: {username}\n\n"
        "Authenticating...\n"
    )

    window.update()

    # ========================================================
    # Netmiko Device
    # ========================================================

    device = {
        "device_type": "juniper_junos",
        "host": ip,
        "username": username,
        "password": password,
        "allow_agent": False
    }

    # ========================================================
    # Connect
    # ========================================================

    try:

        connection = ConnectHandler(
            **device
        )

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
            "Connected successfully!\n\n"
            f"Hostname: {hostname}\n"
            f"IP Address: {ip}\n"
            f"Username: {username}\n"
            f"Credential Mode: {credential_mode}\n"
        )

        start_live_monitoring()

    except Exception as error:

        connection = None
        current_switch = None

        disable_command_buttons()
        stop_live_monitoring()
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
            f"IP Address: {ip}\n"
            f"Username: {username}\n"
            f"Credential Mode: {credential_mode}\n\n"
            f"Error:\n{error}"
        )

        messagebox.showerror(
            "Connection Error",
            f"Could not connect to {hostname}.\n\n"
            + str(error)
        )


# ============================================================
# Ask Status Filter
# ============================================================

def ask_status_filter(title):

    dialog = tk.Toplevel(window)

    dialog.title(title)
    dialog.geometry("300x170")

    dialog.resizable(
        False,
        False
    )

    dialog.transient(window)
    dialog.grab_set()

    selected_status = tk.StringVar(
        value="All"
    )

    label = tk.Label(
        dialog,
        text="Select status:",
        font=("Arial", 11)
    )

    label.pack(
        pady=(20, 5)
    )

    status_combo = ttk.Combobox(
        dialog,
        textvariable=selected_status,
        values=[
            "All",
            "Up",
            "Down"
        ],
        state="readonly",
        width=15
    )

    status_combo.pack(
        pady=5
    )

    result = {
        "value": None
    }

    def confirm():

        result["value"] = selected_status.get()

        dialog.destroy()

    def cancel():

        dialog.destroy()

    button_frame = tk.Frame(
        dialog
    )

    button_frame.pack(
        pady=15
    )

    tk.Button(
        button_frame,
        text="OK",
        width=10,
        command=confirm
    ).pack(
        side="left",
        padx=5
    )

    tk.Button(
        button_frame,
        text="Cancel",
        width=10,
        command=cancel
    ).pack(
        side="left",
        padx=5
    )

    window.wait_window(dialog)

    return result["value"]


# ============================================================
# Get Interface Status
# ============================================================

def get_interface_status():

    result = connection.send_command(
        "show interfaces terse"
    )

    interface_status = {}

    for line in result.splitlines():

        stripped = line.strip()

        if stripped == "":
            continue

        if stripped.startswith("Interface"):
            continue

        parts = stripped.split()

        if len(parts) < 3:
            continue

        interface_name = parts[0]
        admin_status = parts[1]
        link_status = parts[2]

        is_up = (
            admin_status == "up"
            and link_status == "up"
        )

        interface_status[interface_name] = is_up

    return result, interface_status


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

    selected_filter = ask_status_filter(
        "Interface Status"
    )

    if selected_filter is None:
        return

    try:

        result = connection.send_command(
            "show interfaces terse"
        )

        if selected_filter == "All":

            output.delete(
                "1.0",
                tk.END
            )

            output.insert(
                tk.END,
                result
            )

            return

        filtered_lines = []

        for line in result.splitlines():

            stripped = line.strip()

            if stripped.startswith("Interface"):

                filtered_lines.append(line)

                continue

            if stripped == "":
                continue

            parts = stripped.split()

            if len(parts) < 3:
                continue

            admin_status = parts[1]
            link_status = parts[2]

            is_up = (
                admin_status == "up"
                and link_status == "up"
            )

            if selected_filter == "Up":

                if is_up:

                    filtered_lines.append(line)

            elif selected_filter == "Down":

                if not is_up:

                    filtered_lines.append(line)

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            f"Interface Filter: {selected_filter}\n\n"
        )

        if len(filtered_lines) > 1:

            output.insert(
                tk.END,
                "\n".join(filtered_lines)
            )

        else:

            output.insert(
                tk.END,
                "No interfaces found."
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

    selected_filter = ask_status_filter(
        "VLAN Status"
    )

    if selected_filter is None:
        return

    try:

        vlan_result = connection.send_command(
            "show vlans"
        )

        if selected_filter == "All":

            output.delete(
                "1.0",
                tk.END
            )

            output.insert(
                tk.END,
                vlan_result
            )

            return

        interface_result, interface_status = (
            get_interface_status()
        )

        lines = vlan_result.splitlines()

        vlan_blocks = []

        current_block = []
        current_interfaces = []

        for line in lines:

            stripped = line.strip()

            if (
                stripped.startswith("Routing instance")
                or stripped.startswith("VLAN name")
            ):

                if current_block:

                    vlan_blocks.append(
                        (
                            current_block,
                            current_interfaces
                        )
                    )

                    current_block = []
                    current_interfaces = []

                current_block.append(line)

                continue

            if stripped == "":

                if current_block:

                    current_block.append(line)

                continue

            parts = stripped.split()

            interface_name = None

            for part in parts:

                if (
                    part.startswith("ge-")
                    or part.startswith("xe-")
                    or part.startswith("et-")
                    or part.startswith("ae")
                    or part.startswith("irb")
                ):

                    interface_name = part

                    break

            if interface_name is not None:

                if current_block:

                    current_block.append(line)

                    current_interfaces.append(
                        interface_name
                    )

                continue

            if len(parts) >= 2:

                if current_block:

                    vlan_blocks.append(
                        (
                            current_block,
                            current_interfaces
                        )
                    )

                current_block = [line]
                current_interfaces = []

                continue

            if current_block:

                current_block.append(line)

        if current_block:

            vlan_blocks.append(
                (
                    current_block,
                    current_interfaces
                )
            )

        filtered_output = []

        for block, interfaces in vlan_blocks:

            if not interfaces:

                if any(
                    line.strip().startswith(
                        "Routing instance"
                    )
                    for line in block
                ):

                    filtered_output.extend(
                        block
                    )

                continue

            up_interfaces = []
            known_interfaces = []

            for interface in interfaces:

                if interface in interface_status:

                    known_interfaces.append(
                        interface
                    )

                    if interface_status[interface]:

                        up_interfaces.append(
                            interface
                        )

                elif interface.endswith(".0"):

                    physical_interface = (
                        interface[:-2]
                    )

                    if physical_interface in interface_status:

                        known_interfaces.append(
                            physical_interface
                        )

                        if interface_status[
                            physical_interface
                        ]:

                            up_interfaces.append(
                                physical_interface
                            )

            vlan_is_up = (
                len(up_interfaces) > 0
            )

            vlan_is_down = (
                len(known_interfaces) > 0
                and len(up_interfaces) == 0
            )

            if selected_filter == "Up":

                if vlan_is_up:

                    filtered_output.extend(
                        block
                    )

            elif selected_filter == "Down":

                if vlan_is_down:

                    filtered_output.extend(
                        block
                    )

        output.delete(
            "1.0",
            tk.END
        )

        output.insert(
            tk.END,
            f"VLAN Filter: {selected_filter}\n\n"
        )

        if filtered_output:

            output.insert(
                tk.END,
                "\n".join(filtered_output)
            )

        else:

            output.insert(
                tk.END,
                "No VLANs found for this status."
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

    lines = simpledialog.askinteger(
        "Show Logs",
        "How many log lines do you want to display?",
        parent=window,
        minvalue=1
    )

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
# Switch Selection
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
    "1250x900"
)

window.minsize(
    1100,
    800
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
    pady=12
)


# ============================================================
# Authentication Key
# ============================================================

authentication_frame = tk.LabelFrame(
    window,
    text="Switch Password Management",
    padx=10,
    pady=8
)

authentication_frame.pack(
    pady=5
)


authentication_label = tk.Label(
    authentication_frame,
    text="Authentication Key:",
    font=("Arial", 11)
)

authentication_label.pack(
    side="left",
    padx=5
)


authentication_key_entry = tk.Entry(
    authentication_frame,
    width=20
)

authentication_key_entry.insert(
    0,
    "switch-"
)

authentication_key_entry.pack(
    side="left",
    padx=5
)


update_key_button = tk.Button(
    authentication_frame,
    text="Apply Key",
    command=update_authentication_key
)

update_key_button.pack(
    side="left",
    padx=5
)


# ============================================================
# Login Profile
# ============================================================

login_profile_frame = tk.LabelFrame(
    window,
    text="Login Profile",
    padx=10,
    pady=8
)

login_profile_frame.pack(
    pady=5
)


login_username_label = tk.Label(
    login_profile_frame,
    text="Username:",
    font=("Arial", 11)
)

login_username_label.pack(
    side="left",
    padx=5
)


login_username_entry = tk.Entry(
    login_profile_frame,
    width=15
)

login_username_entry.insert(
    0,
    "nour"
)

login_username_entry.pack(
    side="left",
    padx=5
)


login_prefix_label = tk.Label(
    login_profile_frame,
    text="Password Prefix:",
    font=("Arial", 11)
)

login_prefix_label.pack(
    side="left",
    padx=5
)


login_prefix_entry = tk.Entry(
    login_profile_frame,
    width=15
)

login_prefix_entry.insert(
    0,
    "Nour-"
)

login_prefix_entry.pack(
    side="left",
    padx=5
)


use_profile_button = tk.Button(
    login_profile_frame,
    text="Use Login Profile",
    command=use_login_profile
)

use_profile_button.pack(
    side="left",
    padx=5
)


disable_profile_button = tk.Button(
    login_profile_frame,
    text="Disable",
    command=disable_login_profile
)

disable_profile_button.pack(
    side="left",
    padx=5
)


login_profile_status = tk.Label(
    window,
    text="Login Profile: Disabled",
    font=("Arial", 10)
)

login_profile_status.pack(
    pady=3
)


# ============================================================
# Switch Selection
# ============================================================

selection_frame = tk.Frame(
    window
)

selection_frame.pack(
    pady=8
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
# Disconnect Button
# ============================================================

disconnect_button = tk.Button(
    window,
    text="Disconnect",
    width=22,
    command=disconnect_from_switch
)

disconnect_button.pack(
    pady=5
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
    pady=5
)


# ============================================================
# Main Content Area
# ============================================================

main_content_frame = tk.Frame(
    window
)

main_content_frame.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=5
)


# ============================================================
# LEFT SIDE
# ============================================================

left_frame = tk.Frame(
    main_content_frame
)

left_frame.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 10)
)


# ============================================================
# Switch Dashboard
# ============================================================

dashboard_frame = tk.LabelFrame(
    left_frame,
    text="Switch Information",
    padx=15,
    pady=10
)

dashboard_frame.pack(
    fill="x",
    pady=5
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
# Basic Commands
# ============================================================

commands_frame = tk.Frame(
    left_frame
)

commands_frame.pack(
    pady=5
)


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
    left_frame,
    text="Custom Junos Command:",
    font=("Arial", 11)
)

command_label.pack(
    pady=(10, 5)
)


command_suggestions = [
    "show version",
    "show system uptime",
    "show chassis routing-engine",
    "show chassis environment",
    "show chassis alarms",
    "show interfaces terse",
    "show interfaces extensive",
    "show vlans",
    "show ethernet-switching table",
    "show route",
    "show arp",
    "show log messages | last 20",
    "show system processes extensive"
]


command_entry = ttk.Combobox(
    left_frame,
    width=65,
    values=command_suggestions
)

command_entry.pack(
    pady=5
)


run_command_button = tk.Button(
    left_frame,
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
    left_frame,
    text="Command Output:",
    font=("Arial", 11)
)

output_label.pack(
    pady=(10, 5)
)


output = tk.Text(
    left_frame,
    width=75,
    height=15
)

output.pack(
    fill="both",
    expand=True,
    pady=5
)


# ============================================================
# RIGHT SIDE - LIVE MONITORING
# ============================================================

right_frame = tk.Frame(
    main_content_frame,
    width=360
)

right_frame.pack(
    side="right",
    fill="y",
    padx=(10, 0)
)

right_frame.pack_propagate(
    False
)


# ============================================================
# Live Monitoring Frame
# ============================================================

monitor_frame = tk.LabelFrame(
    right_frame,
    text="Live Switch Monitoring",
    padx=15,
    pady=15
)

monitor_frame.pack(
    fill="both",
    expand=True
)


monitor_status = tk.Label(
    monitor_frame,
    text="Monitoring: Stopped",
    anchor="w",
    font=("Arial", 11, "bold")
)

monitor_status.pack(
    fill="x",
    pady=(0, 15)
)


monitor_cpu_load = tk.Label(
    monitor_frame,
    text="CPU Load: -",
    anchor="w",
    font=("Arial", 11)
)

monitor_cpu_load.pack(
    fill="x",
    pady=5
)


monitor_cpu_idle = tk.Label(
    monitor_frame,
    text="CPU Idle: -",
    anchor="w",
    font=("Arial", 11)
)

monitor_cpu_idle.pack(
    fill="x",
    pady=5
)


monitor_load_average = tk.Label(
    monitor_frame,
    text="Load Average: -",
    anchor="w",
    font=("Arial", 11)
)

monitor_load_average.pack(
    fill="x",
    pady=5
)


monitor_temperature = tk.Label(
    monitor_frame,
    text="Temperature: -",
    anchor="w",
    font=("Arial", 11)
)

monitor_temperature.pack(
    fill="x",
    pady=5
)


monitor_routing_engine = tk.Label(
    monitor_frame,
    text="Routing Engine: -",
    anchor="w",
    font=("Arial", 11)
)

monitor_routing_engine.pack(
    fill="x",
    pady=5
)


monitor_alarms = tk.Label(
    monitor_frame,
    text="Chassis Alarms: -",
    anchor="w",
    font=("Arial", 11)
)

monitor_alarms.pack(
    fill="x",
    pady=5
)


separator = ttk.Separator(
    monitor_frame,
    orient="horizontal"
)

separator.pack(
    fill="x",
    pady=15
)


# ============================================================
# Refresh Interval
# ============================================================

refresh_title = tk.Label(
    monitor_frame,
    text="Monitoring Refresh Interval",
    anchor="w",
    font=("Arial", 10, "bold")
)

refresh_title.pack(
    fill="x",
    pady=(0, 5)
)


refresh_interval_frame = tk.Frame(
    monitor_frame
)

refresh_interval_frame.pack(
    fill="x",
    pady=5
)


refresh_interval_label = tk.Label(
    refresh_interval_frame,
    text="Every:",
    font=("Arial", 10)
)

refresh_interval_label.pack(
    side="left"
)


refresh_interval_entry = tk.Entry(
    refresh_interval_frame,
    width=8
)

refresh_interval_entry.insert(
    0,
    str(DEFAULT_REFRESH_SECONDS)
)

refresh_interval_entry.pack(
    side="left",
    padx=5
)


seconds_label = tk.Label(
    refresh_interval_frame,
    text="seconds"
)

seconds_label.pack(
    side="left"
)


apply_refresh_button = tk.Button(
    refresh_interval_frame,
    text="Apply",
    width=8,
    command=apply_refresh_interval
)

apply_refresh_button.pack(
    side="left",
    padx=8
)


# ============================================================
# Last Update
# ============================================================

monitor_last_update = tk.Label(
    monitor_frame,
    text="Last Update: -",
    anchor="w",
    font=("Arial", 10)
)

monitor_last_update.pack(
    fill="x",
    pady=(15, 5)
)


# ============================================================
# Countdown
# ============================================================

monitor_countdown = tk.Label(
    monitor_frame,
    text="Next Refresh: -",
    anchor="w",
    font=("Arial", 10)
)

monitor_countdown.pack(
    fill="x",
    pady=5
)


# ============================================================
# Initialize Dashboard
# ============================================================

clear_dashboard()


# ============================================================
# Start GUI
# ============================================================

window.mainloop()