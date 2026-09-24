import tkinter as tk
from tkinter import ttk, messagebox
from netmiko import ConnectHandler
import json
import os
import re
from datetime import datetime


# ============================================================
# CONFIGURATION
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
    }
]

PASSWORD_DATABASE_FILE = "switch_passwords.json"

connection = None
current_switch = None
current_username = None

refresh_seconds = 60
refresh_job = None


# ============================================================
# PASSWORD DATABASE
# ============================================================

def load_password_database():
    global switches

    if not os.path.exists(PASSWORD_DATABASE_FILE):
        return

    try:
        with open(PASSWORD_DATABASE_FILE, "r") as file:
            saved_data = json.load(file)

        for switch in switches:
            if switch["hostname"] in saved_data:
                switch["password"] = saved_data[
                    switch["hostname"]
                ]

    except Exception as e:
        print("Could not load password database:", e)


def save_password_database():
    data = {}

    for switch in switches:
        data[switch["hostname"]] = switch["password"]

    try:
        with open(PASSWORD_DATABASE_FILE, "w") as file:
            json.dump(data, file, indent=4)

    except Exception as e:
        print("Could not save password database:", e)


load_password_database()


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_selected_switch():

    hostname = switch_combo.get().strip()

    for switch in switches:

        if switch["hostname"] == hostname:
            return switch

    return None


def generate_login_password(switch, prefix):

    last_octet = switch["ip"].split(".")[-1]

    return prefix + last_octet


def validate_username(username):

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9_.-]+",
            username
        )
    )


def validate_prefix(prefix):

    if not prefix:
        return False

    if re.search(r"\s", prefix):
        return False

    return True


def set_status(message, success=False):

    status_label.config(
        text=message
    )

    if success:
        status_label.configure(
            foreground="#16803c"
        )
    else:
        status_label.configure(
            foreground="#444444"
        )


def append_output(text):

    output.config(
        state="normal"
    )

    output.insert(
        tk.END,
        text + "\n"
    )

    output.see(
        tk.END
    )

    output.config(
        state="disabled"
    )


def clear_output():

    output.config(
        state="normal"
    )

    output.delete(
        "1.0",
        tk.END
    )

    output.config(
        state="disabled"
    )


# ============================================================
# CONNECTION
# ============================================================

def login_to_selected_switch():

    global connection
    global current_switch
    global current_username

    selected_switch = get_selected_switch()

    if not selected_switch:

        messagebox.showwarning(
            "Select Switch",
            "Please select a switch first."
        )

        return

    username = login_username_entry.get().strip()
    prefix = login_prefix_entry.get()

    if not username:

        messagebox.showwarning(
            "Username Required",
            "Please enter a username."
        )

        return

    if not prefix:

        messagebox.showwarning(
            "Password Prefix Required",
            "Please enter the password prefix."
        )

        return

    if not validate_username(username):

        messagebox.showerror(
            "Invalid Username",
            "Username can contain letters, numbers, dots, underscores and hyphens."
        )

        return

    if not validate_prefix(prefix):

        messagebox.showerror(
            "Invalid Prefix",
            "Password prefix cannot contain spaces."
        )

        return

    if connection is not None:

        try:
            connection.disconnect()
        except Exception:
            pass

        connection = None

    clear_output()

    append_output(
        f"Connecting to {selected_switch['hostname']} "
        f"({selected_switch['ip']})..."
    )

    password = generate_login_password(
        selected_switch,
        prefix
    )

    device = {
        "device_type": "juniper_junos",
        "host": selected_switch["ip"],
        "username": username,
        "password": password,
        "allow_agent": False
    }

    try:

        connection = ConnectHandler(
            **device
        )

        current_switch = selected_switch
        current_username = username

        append_output(
            "Connected successfully."
        )

        append_output(
            f"Logged in as: {username}"
        )

        append_output("")

        set_status(
            f"Connected to {selected_switch['hostname']} as {username}",
            success=True
        )

        update_dashboard_identity()

        update_dashboard_version()

        start_live_monitoring()

    except Exception as e:

        connection = None
        current_switch = None
        current_username = None

        set_status(
            "Connection failed."
        )

        append_output(
            "Connection failed."
        )

        append_output(
            str(e)
        )

        append_output("")

        update_dashboard_identity()

        messagebox.showerror(
            "Login Failed",
            str(e)
        )


def disconnect_from_switch():

    global connection
    global current_switch
    global current_username

    stop_live_monitoring()

    if connection is not None:

        try:
            connection.disconnect()
        except Exception:
            pass

    connection = None
    current_switch = None
    current_username = None

    update_dashboard_identity()

    set_status(
        "Not connected."
    )

    append_output(
        "Disconnected."
    )

    append_output("")


# ============================================================
# JUNOS USER MANAGEMENT
# ============================================================

def get_privilege_class():

    value = user_privilege_combo.get().strip()

    mapping = {
        "Super User": "super-user",
        "Operator": "operator",
        "Read Only": "read-only"
    }

    return mapping.get(
        value,
        "super-user"
    )


def configure_selected_user():

    selected_switch = get_selected_switch()

    if not selected_switch:

        messagebox.showwarning(
            "Select Switch",
            "Please select a switch first."
        )

        return

    username = user_management_username_entry.get().strip()
    prefix = user_management_prefix_entry.get().strip()

    if not username:

        messagebox.showwarning(
            "Username Required",
            "Please enter a username."
        )

        return

    if not validate_username(username):

        messagebox.showerror(
            "Invalid Username",
            "Username can contain letters, numbers, dots, underscores and hyphens."
        )

        return

    if not validate_prefix(prefix):

        messagebox.showerror(
            "Invalid Prefix",
            "Password prefix cannot contain spaces."
        )

        return

    junos_class = get_privilege_class()

    generated_password = generate_login_password(
        selected_switch,
        prefix
    )

    active_connection = None
    temporary_connection = False

    try:

        if (
            connection is not None
            and current_switch is not None
            and current_switch["hostname"]
            == selected_switch["hostname"]
        ):

            active_connection = connection

        else:

            append_output(
                f"Connecting to {selected_switch['hostname']}..."
            )

            device = {
                "device_type": "juniper_junos",
                "host": selected_switch["ip"],
                "username": "admin",
                "password": selected_switch["password"],
                "allow_agent": False
            }

            active_connection = ConnectHandler(
                **device
            )

            temporary_connection = True

        active_connection.config_mode()

        active_connection.send_command(
            f"set system login user {username} class {junos_class}"
        )

        result = active_connection.send_command_timing(
            f"set system login user {username} authentication plain-text-password"
        )

        if (
            "new password" not in result.lower()
            and "password:" not in result.lower()
        ):

            raise Exception(
                "Juniper did not request a new password."
            )

        active_connection.send_command_timing(
            generated_password
        )

        active_connection.send_command_timing(
            generated_password
        )

        active_connection.commit(
            comment=f"Create/update user {username}"
        )

        append_output("")
        append_output(
            "User configuration completed."
        )

        append_output(
            f"Username: {username}"
        )

        append_output(
            f"Privilege: {junos_class}"
        )

        append_output(
            "Commit completed."
        )

        append_output("")

        messagebox.showinfo(
            "User Updated",
            f"User '{username}' was created or updated successfully."
        )

        close_user_window()

    except Exception as e:

        append_output("")
        append_output(
            "User configuration failed."
        )

        append_output(
            str(e)
        )

        append_output("")

        messagebox.showerror(
            "User Configuration Failed",
            str(e)
        )

    finally:

        if active_connection is not None:

            try:
                active_connection.exit_config_mode()
            except Exception:
                pass

            if temporary_connection:

                try:
                    active_connection.disconnect()
                except Exception:
                    pass


# ============================================================
# USER WINDOW
# ============================================================

user_window = None


def open_user_management():

    global user_window
    global user_management_username_entry
    global user_management_prefix_entry
    global user_privilege_combo

    selected_switch = get_selected_switch()

    if not selected_switch:

        messagebox.showwarning(
            "Select Switch",
            "Please select a switch first."
        )

        return

    if user_window is not None:

        try:

            if user_window.winfo_exists():

                user_window.lift()

                return

        except Exception:
            pass

    user_window = tk.Toplevel(
        root
    )

    user_window.title(
        "Create / Edit User"
    )

    user_window.geometry(
        "430x390"
    )

    user_window.resizable(
        False,
        False
    )

    user_window.transient(
        root
    )

    user_window.grab_set()

    frame = ttk.Frame(
        user_window,
        padding=25
    )

    frame.pack(
        fill="both",
        expand=True
    )

    ttk.Label(
        frame,
        text="Create / Edit User",
        font=("Segoe UI", 16, "bold")
    ).pack(
        anchor="w",
        pady=(0, 20)
    )

    ttk.Label(
        frame,
        text=(
            f"{selected_switch['hostname']} "
            f"({selected_switch['ip']})"
        )
    ).pack(
        anchor="w",
        pady=(0, 18)
    )

    ttk.Label(
        frame,
        text="Username"
    ).pack(
        anchor="w"
    )

    user_management_username_entry = ttk.Entry(
        frame,
        font=("Segoe UI", 11)
    )

    user_management_username_entry.pack(
        fill="x",
        pady=(5, 15)
    )

    ttk.Label(
        frame,
        text="Password Prefix"
    ).pack(
        anchor="w"
    )

    user_management_prefix_entry = ttk.Entry(
        frame,
        font=("Segoe UI", 11)
    )

    user_management_prefix_entry.pack(
        fill="x",
        pady=(5, 15)
    )

    ttk.Label(
        frame,
        text="Privilege"
    ).pack(
        anchor="w"
    )

    user_privilege_combo = ttk.Combobox(
        frame,
        state="readonly",
        values=[
            "Super User",
            "Operator",
            "Read Only"
        ],
        font=("Segoe UI", 10)
    )

    user_privilege_combo.pack(
        fill="x",
        pady=(5, 25)
    )

    user_privilege_combo.set(
        "Super User"
    )

    buttons = ttk.Frame(
        frame
    )

    buttons.pack(
        fill="x"
    )

    ttk.Button(
        buttons,
        text="Save User",
        command=configure_selected_user
    ).pack(
        side="right",
        padx=(8, 0)
    )

    ttk.Button(
        buttons,
        text="Cancel",
        command=close_user_window
    ).pack(
        side="right"
    )

    user_window.protocol(
        "WM_DELETE_WINDOW",
        close_user_window
    )


def close_user_window():

    global user_window

    if user_window is not None:

        try:
            user_window.grab_release()
        except Exception:
            pass

        try:
            user_window.destroy()
        except Exception:
            pass

        user_window = None


# ============================================================
# ADMIN PASSWORD MANAGEMENT
# ============================================================

def change_switch_password(
    switch,
    new_password
):

    device = {
        "device_type": "juniper_junos",
        "host": switch["ip"],
        "username": "admin",
        "password": switch["password"],
        "allow_agent": False
    }

    old_connection = None

    try:

        old_connection = ConnectHandler(
            **device
        )

        old_connection.config_mode()

        result = old_connection.send_command_timing(
            "set system login user admin authentication plain-text-password"
        )

        if (
            "new password" not in result.lower()
            and "password:" not in result.lower()
        ):

            return False, result

        old_connection.send_command_timing(
            new_password
        )

        old_connection.send_command_timing(
            new_password
        )

        commit_result = old_connection.commit(
            comment="Update admin password"
        )

        switch["password"] = new_password

        return True, commit_result

    except Exception as e:

        return False, str(e)

    finally:

        if old_connection is not None:

            try:
                old_connection.disconnect()
            except Exception:
                pass


def open_switch_settings():

    settings_window = tk.Toplevel(
        root
    )

    settings_window.title(
        "Switch Settings"
    )

    settings_window.geometry(
        "500x330"
    )

    settings_window.resizable(
        False,
        False
    )

    settings_window.transient(
        root
    )

    settings_window.grab_set()

    frame = ttk.Frame(
        settings_window,
        padding=25
    )

    frame.pack(
        fill="both",
        expand=True
    )

    ttk.Label(
        frame,
        text="Switch Settings",
        font=("Segoe UI", 16, "bold")
    ).pack(
        anchor="w",
        pady=(0, 20)
    )

    ttk.Label(
        frame,
        text="Authentication Key"
    ).pack(
        anchor="w"
    )

    authentication_key_entry = ttk.Entry(
        frame,
        font=("Segoe UI", 11),
        show="*"
    )

    authentication_key_entry.pack(
        fill="x",
        pady=(5, 20)
    )

    def apply_key():

        authentication_key = (
            authentication_key_entry
            .get()
            .strip()
        )

        if not authentication_key:

            messagebox.showwarning(
                "Authentication Key",
                "Please enter an authentication key."
            )

            return

        confirm = messagebox.askyesno(
            "Confirm",
            "Update the admin account on all switches?"
        )

        if not confirm:
            return

        disconnect_from_switch()

        success_count = 0

        for switch in switches:

            last_part = switch["ip"].split(".")[-1]

            new_password = (
                authentication_key
                + last_part
            )

            success, result = change_switch_password(
                switch,
                new_password
            )

            if success:

                success_count += 1

                append_output(
                    f"{switch['hostname']}: admin account updated."
                )

            else:

                append_output(
                    f"{switch['hostname']}: update failed."
                )

                append_output(
                    str(result)
                )

        save_password_database()

        messagebox.showinfo(
            "Completed",
            f"{success_count} switch(es) updated."
        )

        settings_window.destroy()

    buttons = ttk.Frame(
        frame
    )

    buttons.pack(
        side="bottom",
        fill="x"
    )

    ttk.Button(
        buttons,
        text="Apply",
        command=apply_key
    ).pack(
        side="right",
        padx=(8, 0)
    )

    ttk.Button(
        buttons,
        text="Cancel",
        command=settings_window.destroy
    ).pack(
        side="right"
    )


# ============================================================
# COMMAND FUNCTIONS
# ============================================================

def require_connection():

    if connection is None:

        messagebox.showwarning(
            "Not Connected",
            "Please login to a switch first."
        )

        return False

    return True


def show_version():

    if not require_connection():
        return

    try:

        result = connection.send_command(
            "show version"
        )

        append_output(
            result
        )

    except Exception as e:

        append_output(
            str(e)
        )


def show_interfaces():

    if not require_connection():
        return

    try:

        result = connection.send_command(
            "show interfaces terse"
        )

        append_output(
            result
        )

    except Exception as e:

        append_output(
            str(e)
        )


def show_vlans():

    if not require_connection():
        return

    try:

        result = connection.send_command(
            "show vlans"
        )

        append_output(
            result
        )

    except Exception as e:

        append_output(
            str(e)
        )


def show_logs():

    if not require_connection():
        return

    try:

        result = connection.send_command(
            "show log messages | last 50"
        )

        append_output(
            result
        )

    except Exception as e:

        append_output(
            str(e)
        )


def restart_switch():

    if not require_connection():
        return

    confirm = messagebox.askyesno(
        "Restart Switch",
        "Are you sure you want to restart the switch?"
    )

    if not confirm:
        return

    try:

        result = connection.send_command_timing(
            "request system reboot"
        )

        append_output(
            result
        )

    except Exception as e:

        append_output(
            str(e)
        )


def run_custom_command():

    if not require_connection():
        return

    command = command_entry.get().strip()

    if not command:
        return

    append_output(
        f"{current_username}@"
        f"{current_switch['hostname']}> "
        f"{command}"
    )

    try:

        result = connection.send_command(
            command
        )

        append_output(
            result
        )

        append_output("")

    except Exception as e:

        append_output(
            str(e)
        )

        append_output("")


# ============================================================
# DASHBOARD
# ============================================================

def update_dashboard_identity():

    if current_switch is None:

        dashboard_hostname_value.config(
            text="-"
        )

        dashboard_ip_value.config(
            text="-"
        )

        dashboard_username_value.config(
            text="-"
        )

        dashboard_status_value.config(
            text="Not connected"
        )

        dashboard_model_value.config(
            text="-"
        )

        dashboard_junos_value.config(
            text="-"
        )

        dashboard_uptime_value.config(
            text="-"
        )

        return

    dashboard_hostname_value.config(
        text=current_switch["hostname"]
    )

    dashboard_ip_value.config(
        text=current_switch["ip"]
    )

    dashboard_username_value.config(
        text=current_username or "-"
    )

    dashboard_status_value.config(
        text="Connected"
    )


def update_dashboard_version():

    if connection is None:
        return

    try:

        version = connection.send_command(
            "show version"
        )

        dashboard_model_value.config(
            text=get_model_from_version(
                version
            )
        )

        dashboard_junos_value.config(
            text=get_junos_from_version(
                version
            )
        )

        dashboard_uptime_value.config(
            text=parse_system_uptime(
                version
            )
        )

    except Exception as e:

        append_output(
            f"Dashboard version error: {e}"
        )


# ============================================================
# LIVE MONITORING PARSERS
# ============================================================

def parse_system_processes(output_text):

    result = {
        "cpu_idle": None,
        "cpu_usage": None,
        "load_average": "-"
    }

    # --------------------------------------------------------
    # Load average
    #
    # Typical:
    # load averages: 0.12, 0.10, 0.08
    # --------------------------------------------------------

    load_match = re.search(
        r"load averages:\s*"
        r"([\d.]+)\s*,\s*"
        r"([\d.]+)\s*,\s*"
        r"([\d.]+)",
        output_text,
        re.IGNORECASE
    )

    if load_match:

        result["load_average"] = (
            f"{load_match.group(1)}, "
            f"{load_match.group(2)}, "
            f"{load_match.group(3)}"
        )

    # --------------------------------------------------------
    # CPU idle
    #
    # show system processes extensive commonly contains
    # an idle process with WCPU percentage.
    #
    # Example:
    # 10 root ... idle ... 0.00%
    #
    # We also support:
    # 94.0% idle
    # --------------------------------------------------------

    idle_match = re.search(
        r"(\d+(?:\.\d+)?)%\s+idle",
        output_text,
        re.IGNORECASE
    )

    if idle_match:

        result["cpu_idle"] = float(
            idle_match.group(1)
        )

    else:

        # Look for a process named idle.
        idle_process_matches = re.findall(
            r"\bidle(?::\s*cpu\d+)?\b.*?"
            r"(\d+(?:\.\d+)?)%",
            output_text,
            re.IGNORECASE
        )

        if idle_process_matches:

            try:

                idle_values = [
                    float(value)
                    for value in idle_process_matches
                ]

                # For the idle process, the WCPU value is
                # usually the percentage of CPU that is idle.
                idle_value = max(
                    idle_values
                )

                if 0 <= idle_value <= 100:
                    result["cpu_idle"] = idle_value

            except Exception:
                pass

    if result["cpu_idle"] is not None:

        result["cpu_usage"] = round(
            100 - result["cpu_idle"],
            1
        )

    return result


def parse_temperature(output_text):

    temperatures = []

    # --------------------------------------------------------
    # EX2300 examples:
    #
    # FPC 0 CPU Sensor   OK   37 degrees C / 98 degrees F
    #
    # Routing Engine 0 CPU Temperature OK
    # 45 degrees C / 113 degrees F
    # --------------------------------------------------------

    # Prefer CPU / Routing Engine temperatures.
    cpu_temperature_matches = re.findall(
        r"(?:CPU Sensor|CPU Temperature|Routing Engine.*?CPU)"
        r".*?"
        r"(\d+)\s+degrees\s+C",
        output_text,
        re.IGNORECASE
    )

    for value in cpu_temperature_matches:

        try:
            temperatures.append(
                int(value)
            )
        except Exception:
            pass

    # If no CPU-specific temperature exists,
    # use all chassis temperature sensors.
    if not temperatures:

        all_temperature_matches = re.findall(
            r"(\d+)\s+degrees\s+C",
            output_text,
            re.IGNORECASE
        )

        for value in all_temperature_matches:

            try:
                temperatures.append(
                    int(value)
                )
            except Exception:
                pass

    if temperatures:

        # Display the highest relevant temperature.
        return f"{max(temperatures)} °C"

    return "-"


def parse_alarms(output_text):

    text = output_text.strip()

    if not text:

        return "-"

    lower = text.lower()

    if (
        "no alarms currently active"
        in lower
    ):

        return "None"

    if re.search(
        r"\d+\s+alarms?\s+currently\s+active",
        lower
    ):

        return "Active"

    return "None"


def parse_routing_engine_status(output_text):

    # --------------------------------------------------------
    # Typical:
    #
    # Routing Engine status:
    #   Slot 0:
    #     Current state       Master
    #
    # or:
    #
    # State Online Master
    # --------------------------------------------------------

    if re.search(
        r"\bMaster\b",
        output_text,
        re.IGNORECASE
    ):

        return "Online - Master"

    if re.search(
        r"\bBackup\b",
        output_text,
        re.IGNORECASE
    ):

        return "Online - Backup"

    if re.search(
        r"\bOnline\b",
        output_text,
        re.IGNORECASE
    ):

        return "Online"

    return "-"


def parse_system_uptime(output_text):

    # --------------------------------------------------------
    # show version:
    #
    # System uptime: 1 day, 2 hours, 30 minutes
    # --------------------------------------------------------

    match = re.search(
        r"System uptime:\s*(.+)",
        output_text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return "-"


def get_model_from_version(version_output):

    # EX2300 usually:
    # Model: ex2300-48p
    #
    # Sometimes model may be listed as:
    # Model: EX2300-48P
    #

    match = re.search(
        r"Model:\s*(\S+)",
        version_output,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    # Alternative format.
    match = re.search(
        r"model\s*[:=]\s*(\S+)",
        version_output,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return "-"


def get_junos_from_version(version_output):

    # Typical:
    # JUNOS Software Release [20.4R3-S2.6]
    #
    # or:
    # Junos: 20.4R3-S2.6

    match = re.search(
        r"Junos:\s*(\S+)",
        version_output,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    match = re.search(
        r"JUNOS Software Release\s*\[([^\]]+)\]",
        version_output,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return "-"


# ============================================================
# LIVE MONITORING
# ============================================================

def refresh_live_monitoring():

    global refresh_job

    if connection is None:

        stop_live_monitoring()

        return

    try:

        # ====================================================
        # CPU + LOAD
        # ====================================================

        process_output = connection.send_command(
            "show system processes extensive",
            read_timeout=15
        )

        process_data = parse_system_processes(
            process_output
        )

        # ====================================================
        # TEMPERATURE
        # ====================================================

        environment_output = connection.send_command(
            "show chassis environment",
            read_timeout=15
        )

        temperature = parse_temperature(
            environment_output
        )

        # ====================================================
        # CHASSIS ALARMS
        # ====================================================

        alarms_output = connection.send_command(
            "show chassis alarms",
            read_timeout=15
        )

        alarms = parse_alarms(
            alarms_output
        )

        # ====================================================
        # ROUTING ENGINE
        # ====================================================

        routing_output = connection.send_command(
            "show chassis routing-engine",
            read_timeout=15
        )

        routing_engine = parse_routing_engine_status(
            routing_output
        )

        # ====================================================
        # VERSION
        # ====================================================

        version_output = connection.send_command(
            "show version",
            read_timeout=15
        )

        model = get_model_from_version(
            version_output
        )

        junos = get_junos_from_version(
            version_output
        )

        uptime = parse_system_uptime(
            version_output
        )

        # ====================================================
        # UPDATE CPU
        # ====================================================

        cpu_idle = process_data["cpu_idle"]
        cpu_usage = process_data["cpu_usage"]

        if cpu_usage is not None:

            cpu_usage_value.config(
                text=f"{cpu_usage:.1f}%"
            )

        else:

            cpu_usage_value.config(
                text="-"
            )

        if cpu_idle is not None:

            cpu_idle_value.config(
                text=f"{cpu_idle:.1f}%"
            )

        else:

            cpu_idle_value.config(
                text="-"
            )

        # ====================================================
        # UPDATE LOAD
        # ====================================================

        load_average_value.config(
            text=process_data["load_average"]
        )

        # ====================================================
        # UPDATE TEMPERATURE
        # ====================================================

        temperature_value.config(
            text=temperature
        )

        # ====================================================
        # UPDATE ROUTING ENGINE
        # ====================================================

        routing_engine_value.config(
            text=routing_engine
        )

        # ====================================================
        # UPDATE ALARMS
        # ====================================================

        alarms_value.config(
            text=alarms
        )

        # ====================================================
        # UPDATE SWITCH DETAILS
        # ====================================================

        dashboard_model_value.config(
            text=model
        )

        dashboard_junos_value.config(
            text=junos
        )

        dashboard_uptime_value.config(
            text=uptime
        )

        # ====================================================
        # LAST UPDATE
        # ====================================================

        last_update_value.config(
            text=datetime.now().strftime(
                "%H:%M:%S"
            )
        )

        # ====================================================
        # SCHEDULE NEXT UPDATE
        # ====================================================

        schedule_refresh()

    except Exception as e:

        append_output(
            "Monitoring error:"
        )

        append_output(
            str(e)
        )

        # Try again at the next interval.
        schedule_refresh()


def schedule_refresh():

    global refresh_job

    if connection is None:
        return

    if refresh_job is not None:

        try:

            root.after_cancel(
                refresh_job
            )

        except Exception:
            pass

    refresh_job = root.after(
        refresh_seconds * 1000,
        refresh_live_monitoring
    )


def start_live_monitoring():

    refresh_live_monitoring()


def stop_live_monitoring():

    global refresh_job

    if refresh_job is not None:

        try:

            root.after_cancel(
                refresh_job
            )

        except Exception:
            pass

        refresh_job = None

    cpu_usage_value.config(
        text="-"
    )

    cpu_idle_value.config(
        text="-"
    )

    load_average_value.config(
        text="-"
    )

    temperature_value.config(
        text="-"
    )

    routing_engine_value.config(
        text="-"
    )

    alarms_value.config(
        text="-"
    )

    last_update_value.config(
        text="-"
    )


# ============================================================
# REFRESH SETTINGS
# ============================================================

def apply_refresh_time():

    global refresh_seconds

    value = refresh_entry.get().strip()

    try:

        seconds = int(value)

        if seconds < 5:
            raise ValueError

    except ValueError:

        messagebox.showerror(
            "Invalid Refresh Time",
            "Enter a number of seconds greater than or equal to 5."
        )

        return

    refresh_seconds = seconds

    if connection is not None:

        schedule_refresh()

    set_status(
        f"Refresh interval set to {refresh_seconds} seconds."
    )


# ============================================================
# SWITCH SELECTION
# ============================================================

def switch_selected(event=None):

    selected_switch = get_selected_switch()

    if not selected_switch:
        return

    if connection is not None:

        disconnect_from_switch()

    dashboard_hostname_value.config(
        text="-"
    )

    dashboard_ip_value.config(
        text=selected_switch["ip"]
    )

    dashboard_username_value.config(
        text="-"
    )

    dashboard_status_value.config(
        text="Not connected"
    )

    dashboard_model_value.config(
        text="-"
    )

    dashboard_junos_value.config(
        text="-"
    )

    dashboard_uptime_value.config(
        text="-"
    )

    set_status(
        f"Selected {selected_switch['hostname']} "
        f"({selected_switch['ip']})"
    )


# ============================================================
# WINDOW CLOSE
# ============================================================

def on_closing():

    disconnect_from_switch()

    root.destroy()


# ============================================================
# GUI
# ============================================================

root = tk.Tk()

root.title(
    "Juniper Switch Manager"
)

root.geometry(
    "1400x920"
)

root.minsize(
    1150,
    780
)

root.protocol(
    "WM_DELETE_WINDOW",
    on_closing
)


# ============================================================
# STYLES
# ============================================================

style = ttk.Style()

try:
    style.theme_use("clam")
except Exception:
    pass

style.configure(
    "Title.TLabel",
    font=("Segoe UI", 22)
)

style.configure(
    "Section.TLabelframe.Label",
    font=("Segoe UI", 11)
)

style.configure(
    "DashboardValue.TLabel",
    font=("Segoe UI", 10)
)

style.configure(
    "DashboardLabel.TLabel",
    font=("Segoe UI", 10)
)

style.configure(
    "Action.TButton",
    font=("Segoe UI", 10),
    padding=(12, 7)
)


# ============================================================
# MAIN CONTAINER
# ============================================================

main_container = ttk.Frame(
    root,
    padding=15
)

main_container.pack(
    fill="both",
    expand=True
)


# ============================================================
# HEADER
# ============================================================

header_frame = ttk.Frame(
    main_container
)

header_frame.pack(
    fill="x",
    pady=(0, 12)
)

ttk.Label(
    header_frame,
    text="Juniper Switch Manager",
    style="Title.TLabel"
).pack(
    side="left"
)

ttk.Button(
    header_frame,
    text="Switch Settings",
    command=open_switch_settings
).pack(
    side="right"
)


# ============================================================
# SWITCH ACCESS
# ============================================================

control_frame = ttk.LabelFrame(
    main_container,
    text="Switch Access",
    padding=12
)

control_frame.pack(
    fill="x",
    pady=(0, 8)
)


# Switch

ttk.Label(
    control_frame,
    text="Switch"
).grid(
    row=0,
    column=0,
    padx=(0, 8),
    pady=5,
    sticky="w"
)

switch_combo = ttk.Combobox(
    control_frame,
    state="readonly",
    width=22,
    values=[
        switch["hostname"]
        for switch in switches
    ]
)

switch_combo.grid(
    row=0,
    column=1,
    padx=(0, 20),
    pady=5,
    sticky="ew"
)

switch_combo.set(
    "Select a switch"
)

switch_combo.bind(
    "<<ComboboxSelected>>",
    switch_selected
)


# Username

ttk.Label(
    control_frame,
    text="Username"
).grid(
    row=0,
    column=2,
    padx=(0, 8),
    pady=5,
    sticky="w"
)

login_username_entry = ttk.Entry(
    control_frame,
    width=18
)

login_username_entry.grid(
    row=0,
    column=3,
    padx=(0, 20),
    pady=5,
    sticky="ew"
)


# Prefix

ttk.Label(
    control_frame,
    text="Password Prefix"
).grid(
    row=0,
    column=4,
    padx=(0, 8),
    pady=5,
    sticky="w"
)

login_prefix_entry = ttk.Entry(
    control_frame,
    width=18,
    show="*"
)

login_prefix_entry.grid(
    row=0,
    column=5,
    padx=(0, 20),
    pady=5,
    sticky="ew"
)


# Login

ttk.Button(
    control_frame,
    text="Login",
    style="Action.TButton",
    command=login_to_selected_switch
).grid(
    row=0,
    column=6,
    padx=(0, 8),
    pady=5
)


# Create / Edit User

ttk.Button(
    control_frame,
    text="Create / Edit User",
    style="Action.TButton",
    command=open_user_management
).grid(
    row=0,
    column=7,
    padx=(0, 8),
    pady=5
)


# Disconnect

ttk.Button(
    control_frame,
    text="Disconnect",
    command=disconnect_from_switch
).grid(
    row=0,
    column=8,
    pady=5
)


control_frame.columnconfigure(
    1,
    weight=1
)

control_frame.columnconfigure(
    3,
    weight=1
)

control_frame.columnconfigure(
    5,
    weight=1
)


# ============================================================
# LOGIN HELP
# ============================================================

login_info_frame = ttk.Frame(
    main_container
)

login_info_frame.pack(
    fill="x",
    pady=(0, 8)
)

ttk.Label(
    login_info_frame,
    text="Select a switch and enter your credentials to login."
).pack(
    anchor="w"
)


# ============================================================
# STATUS
# ============================================================

status_frame = ttk.Frame(
    main_container
)

status_frame.pack(
    fill="x",
    pady=(0, 8)
)

ttk.Label(
    status_frame,
    text="Status:"
).pack(
    side="left"
)

status_label = ttk.Label(
    status_frame,
    text="Select a switch"
)

status_label.pack(
    side="left",
    padx=(6, 0)
)


# ============================================================
# DASHBOARD
# ============================================================

dashboard_frame = ttk.LabelFrame(
    main_container,
    text="Dashboard",
    padding=10
)

dashboard_frame.pack(
    fill="x",
    pady=(0, 8)
)

dashboard_frame.columnconfigure(
    0,
    weight=1
)

dashboard_frame.columnconfigure(
    1,
    weight=1
)


# ============================================================
# LEFT - SWITCH DETAILS
# ============================================================

details_frame = ttk.LabelFrame(
    dashboard_frame,
    text="Switch Details",
    padding=10
)

details_frame.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 5)
)


def create_detail_row(
    parent,
    row,
    label_text
):

    ttk.Label(
        parent,
        text=label_text
    ).grid(
        row=row,
        column=0,
        padx=8,
        pady=4,
        sticky="w"
    )

    value = ttk.Label(
        parent,
        text="-"
    )

    value.grid(
        row=row,
        column=1,
        padx=8,
        pady=4,
        sticky="w"
    )

    return value


dashboard_hostname_value = create_detail_row(
    details_frame,
    0,
    "Hostname"
)

dashboard_ip_value = create_detail_row(
    details_frame,
    1,
    "IP Address"
)

dashboard_username_value = create_detail_row(
    details_frame,
    2,
    "Username"
)

dashboard_status_value = create_detail_row(
    details_frame,
    3,
    "Status"
)

dashboard_model_value = create_detail_row(
    details_frame,
    4,
    "Model"
)

dashboard_junos_value = create_detail_row(
    details_frame,
    5,
    "Junos"
)

dashboard_uptime_value = create_detail_row(
    details_frame,
    6,
    "System Uptime"
)


# ============================================================
# RIGHT - SYSTEM HEALTH
# ============================================================

health_frame = ttk.LabelFrame(
    dashboard_frame,
    text="System Health",
    padding=10
)

health_frame.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=(5, 0)
)

cpu_usage_value = create_detail_row(
    health_frame,
    0,
    "CPU Usage"
)

cpu_idle_value = create_detail_row(
    health_frame,
    1,
    "CPU Idle"
)

load_average_value = create_detail_row(
    health_frame,
    2,
    "Load Average"
)

temperature_value = create_detail_row(
    health_frame,
    3,
    "Temperature"
)

routing_engine_value = create_detail_row(
    health_frame,
    4,
    "Routing Engine"
)

alarms_value = create_detail_row(
    health_frame,
    5,
    "Chassis Alarms"
)

last_update_value = create_detail_row(
    health_frame,
    6,
    "Last Update"
)


# ============================================================
# REFRESH SETTINGS
# ============================================================

refresh_frame = ttk.Frame(
    main_container
)

refresh_frame.pack(
    fill="x",
    pady=(0, 8)
)

ttk.Label(
    refresh_frame,
    text="Refresh every"
).pack(
    side="left"
)

refresh_entry = ttk.Entry(
    refresh_frame,
    width=7
)

refresh_entry.insert(
    0,
    "60"
)

refresh_entry.pack(
    side="left",
    padx=(6, 5)
)

ttk.Label(
    refresh_frame,
    text="seconds"
).pack(
    side="left"
)

ttk.Button(
    refresh_frame,
    text="Apply",
    command=apply_refresh_time
).pack(
    side="left",
    padx=(10, 0)
)


# ============================================================
# MAIN CONTENT / CLI
# ============================================================

main_pane = tk.PanedWindow(
    main_container,
    orient="vertical",
    sashrelief="raised",
    sashwidth=6,
    bg="#d0d0d0"
)

main_pane.pack(
    fill="both",
    expand=True
)


# ============================================================
# CLI CONSOLE
# ============================================================

console_frame = ttk.LabelFrame(
    main_pane,
    text="CLI Console",
    padding=8
)

main_pane.add(
    console_frame,
    minsize=300
)


# Command bar

command_bar = ttk.Frame(
    console_frame
)

command_bar.pack(
    fill="x",
    pady=(0, 8)
)

ttk.Label(
    command_bar,
    text="Command"
).pack(
    side="left",
    padx=(0, 8)
)

command_entry = ttk.Combobox(
    command_bar,
    font=("Consolas", 10),
    values=[
        "show version",
        "show system processes extensive",
        "show interfaces terse",
        "show vlans",
        "show chassis routing-engine",
        "show chassis environment",
        "show chassis environment routing-engine",
        "show chassis alarms",
        "show log messages | last 50",
        "show configuration"
    ]
)

command_entry.pack(
    side="left",
    fill="x",
    expand=True
)

ttk.Button(
    command_bar,
    text="Run",
    style="Action.TButton",
    command=run_custom_command
).pack(
    side="left",
    padx=(8, 0)
)

ttk.Button(
    command_bar,
    text="Clear",
    command=clear_output
).pack(
    side="left",
    padx=(8, 0)
)


# ============================================================
# OUTPUT
# ============================================================

output_frame = ttk.Frame(
    console_frame
)

output_frame.pack(
    fill="both",
    expand=True
)

output_frame.rowconfigure(
    0,
    weight=1
)

output_frame.columnconfigure(
    0,
    weight=1
)

output = tk.Text(
    output_frame,
    wrap="none",
    font=("Consolas", 10),
    bg="#111111",
    fg="#eeeeee",
    insertbackground="white",
    padx=10,
    pady=10
)

output.grid(
    row=0,
    column=0,
    sticky="nsew"
)

vertical_scrollbar = ttk.Scrollbar(
    output_frame,
    orient="vertical",
    command=output.yview
)

vertical_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns"
)

horizontal_scrollbar = ttk.Scrollbar(
    output_frame,
    orient="horizontal",
    command=output.xview
)

horizontal_scrollbar.grid(
    row=1,
    column=0,
    sticky="ew"
)

output.configure(
    yscrollcommand=vertical_scrollbar.set,
    xscrollcommand=horizontal_scrollbar.set
)

output.config(
    state="disabled"
)


# ============================================================
# STARTUP
# ============================================================

append_output(
    "Juniper Switch Manager ready."
)

append_output(
    "Select a switch and login to begin."
)

append_output("")


# ============================================================
# START APPLICATION
# ============================================================

root.mainloop()