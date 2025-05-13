from pynput import mouse, keyboard
import psutil
import time
import contextlib
import sys
from threading import Timer
import configparser
from datetime import datetime
from models import Session, MonitoredProcess, ProcessActivityLog, Base, engine
import os
import keyboard as kb
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

# Import custom modules
from console_utils import (
    print_header, print_menu, print_info, print_success,
    print_warning, print_error, clear_screen, MonitoringDisplay,
    console, COLOR_PRIMARY, COLOR_WARNING, COLOR_ACCENT
)
from export_utils import export_to_excel, export_to_pdf
from config_editor import edit_config
from trial_license_manager import TrialLicenseManager

# Initialize the trial license manager
LICENSE_MANAGER = TrialLicenseManager(
    app_name="ProcessActivityMonitor",
    trial_days=7,
    enable_online_verification=True,
    cache_duration=3600  # Cache license status for 1 hour
)

def clear_database():
    # Drop all tables
    Base.metadata.drop_all(engine)
    # Recreate all tables
    Base.metadata.create_all(engine)

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

CONFIG = {
    'target_processes': [p.strip().lower() for p in config['ProcessWatchdog']['target_processes'].split(',')],
    'poll_interval': config['ProcessWatchdog'].getfloat('poll_interval'),
    'inactivity_timeout': config['ProcessWatchdog'].getfloat('inactivity_timeout')
}

class ProcessMonitor:
    def __init__(self, process_name):
        self.process_name = process_name
        self.last_activity_time = time.time()
        self.pid = None
        self.inactivity_timer = None
        self.session = Session()
        self.monitored_process = None
        self.current_activity_log = None
        self.is_inactive = False

    def reset_timer(self):
        self.last_activity_time = time.time()
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        self.inactivity_timer = Timer(CONFIG['inactivity_timeout'], self.on_inactivity)
        self.inactivity_timer.start()

        # If coming back from inactivity, create new session
        if self.is_inactive and self.pid:
            self.is_inactive = False
            self._create_new_activity_log()
        # Update last activity time
        elif self.current_activity_log:
            self.current_activity_log.last_activity_time = datetime.now()
            self.monitored_process.last_seen = datetime.now()
            self.session.commit()

    def on_inactivity(self):
        if self.pid and psutil.pid_exists(self.pid):
            try:
                # Update records
                if self.current_activity_log:
                    current_time = datetime.now()
                    self.current_activity_log.end_time = current_time
                    # Calculate session duration as end_time - start_time
                    duration = (current_time - self.current_activity_log.start_time).total_seconds()
                    self.current_activity_log.session_uptime_seconds = duration

                if self.monitored_process:
                    process = psutil.Process(self.pid)
                    self.monitored_process.last_uptime_seconds = time.time() - process.create_time()

                self.session.commit()
                self.is_inactive = True

            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"Failed to get process info for {self.process_name}: {e}")

    def _create_new_activity_log(self):
        current_time = datetime.now()
        # Create new activity log
        self.current_activity_log = ProcessActivityLog(
            process_id=self.monitored_process.id,
            start_time=current_time,
            last_activity_time=current_time
        )
        self.session.add(self.current_activity_log)
        self.session.commit()

    def update_pid(self, new_pid):
        current_time = datetime.now()

        # Close current activity log if exists
        if self.current_activity_log:
            self.current_activity_log.end_time = current_time
            # Calculate final session duration
            duration = (current_time - self.current_activity_log.start_time).total_seconds()
            self.current_activity_log.session_uptime_seconds = duration
            self.session.commit()

        # Update PID and process record
        if new_pid != self.pid:
            self.pid = new_pid

            # Update or create monitored process record
            if self.monitored_process is None or self.monitored_process.pid != new_pid:
                self.monitored_process = MonitoredProcess(
                    process_name=self.process_name,
                    pid=new_pid,
                    last_seen=current_time
                )
                self.session.add(self.monitored_process)
                self.session.flush()  # To get the ID

            self._create_new_activity_log()

        self.reset_timer()

    def cleanup(self):
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        if self.current_activity_log:
            current_time = datetime.now()
            self.current_activity_log.end_time = current_time
            # Calculate final session duration
            duration = (current_time - self.current_activity_log.start_time).total_seconds()
            self.current_activity_log.session_uptime_seconds = duration
            self.session.commit()
        self.session.close()

class ActivityMonitor:
    def __init__(self, target_processes):
        self.process_monitors = {
            process_name.lower(): ProcessMonitor(process_name)
            for process_name in target_processes
        }

    def cleanup(self):
        for monitor in self.process_monitors.values():
            monitor.cleanup()

def get_active_process_name_and_pid():
    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None, None

        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        if pid <= 0 or not psutil.pid_exists(pid):
            return None, None

        process = psutil.Process(pid)
        process_name = process.name()
        return process_name, pid

    except Exception as e:
        print(f"Error getting process info: {e}")
        return None, None

def create_activity_handler(monitor):
    def on_activity(x=None, y=None):
        process_name, pid = get_active_process_name_and_pid()
        if process_name:
            process_name = process_name.lower()
            if process_name in monitor.process_monitors:
                monitor.process_monitors[process_name].update_pid(pid)
    return on_activity

@contextlib.contextmanager
def create_listeners(monitor):
    on_activity = create_activity_handler(monitor)
    mouse_listener = mouse.Listener(on_move=on_activity)
    keyboard_listener = keyboard.Listener(on_press=lambda key: on_activity())

    mouse_listener.start()
    keyboard_listener.start()

    try:
        yield
    finally:
        monitor.cleanup()
        mouse_listener.stop()
        keyboard_listener.stop()

def display_last_log():
    """Display the most recent activity logs."""
    clear_screen()
    print_header("Recent Activity Logs", "Process Activity Monitor")

    session = Session()
    try:
        # Get the most recent logs (last 24 hours)
        from query_logs import print_recent_activity
        print_recent_activity(24)

        print_info("\nPress Enter to return to the main menu...")
        input()
    finally:
        session.close()

def start_monitoring():
    """Start the process monitoring function."""
    # Clear database on startup
    clear_database()

    # Initialize monitoring
    monitor = ActivityMonitor(CONFIG['target_processes'])
    start_time = time.time()

    # Create monitoring display
    display = MonitoringDisplay(monitor.process_monitors, start_time)

    try:
        with create_listeners(monitor):
            # Start the live display
            display.start()

            # Keep running until Ctrl+Q is pressed
            while display.running:
                time.sleep(0.1)

            print_info("Monitoring stopped. Returning to main menu...")
            time.sleep(1)
    except Exception as e:
        print_error(f"Error during monitoring: {e}")
        time.sleep(2)

def export_report():
    """Export monitoring data to Excel or PDF."""
    clear_screen()
    print_header("Export Report", "Process Activity Monitor")

    options = [
        ("1", "Export to Excel"),
        ("2", "Export to PDF"),
        ("q", "Return to Main Menu")
    ]

    print_menu("Select Export Format", options)

    choice = Prompt.ask(
        "Select an option",
        choices=["1", "2", "q", "Q"],
        default="q"
    )

    if choice.lower() == 'q':
        return

    try:
        if choice == '1':
            filename = export_to_excel()
            print_success(f"Report exported to Excel: {filename}")
        elif choice == '2':
            filename = export_to_pdf()
            print_success(f"Report exported to PDF: {filename}")

        print_info("\nPress Enter to return to the main menu...")
        input()
    except Exception as e:
        print_error(f"Error exporting report: {e}")
        print_info("\nPress Enter to return to the main menu...")
        input()

def show_trial_info():
    """Display trial information."""
    clear_screen()

    # Check trial status
    remaining_days = LICENSE_MANAGER.get_remaining_days()

    if not LICENSE_MANAGER.is_trial_valid():
        # Trial has been corrupted or expired
        text = Text("TRIAL EXPIRED", style=f"bold {COLOR_WARNING}")
        panel = Panel(
            Align.center(text),
            title="Process Activity Monitor",
            border_style=COLOR_WARNING
        )
        console.print(panel)
        console.print()
        console.print("Your trial period has expired. The application will now exit.")
        console.print("Please contact support to purchase a full license.")
        console.print()
        console.print("Press Enter to exit...")
        input()
        sys.exit(1)
    else:
        # Trial is still valid
        days_text = f"{remaining_days:.1f}" if remaining_days < 1 else f"{int(remaining_days)}"
        text = Text(f"TRIAL VERSION - {days_text} DAYS REMAINING", style=f"bold {COLOR_ACCENT}")
        panel = Panel(
            Align.center(text),
            title="Process Activity Monitor",
            border_style=COLOR_ACCENT
        )
        console.print(panel)
        console.print()
        console.print("This is a trial version of Process Activity Monitor.")
        console.print(f"You have {days_text} days remaining in your trial period.")
        console.print("After the trial expires, the application will no longer function.")
        console.print()
        console.print("Press Enter to continue...")
        input()

def main():
    """Main application entry point with menu system."""
    # Check if trial is valid
    if not LICENSE_MANAGER.is_trial_valid():
        # Trial has expired or been corrupted
        clear_screen()
        text = Text("TRIAL EXPIRED", style=f"bold {COLOR_WARNING}")
        panel = Panel(
            Align.center(text),
            title="Process Activity Monitor",
            border_style=COLOR_WARNING
        )
        console.print(panel)
        console.print()
        console.print("Your trial period has expired. The application will now exit.")
        console.print("Please contact support to purchase a full license.")
        console.print()
        console.print("Press Enter to exit...")
        input()

        # Corrupt the trial data to prevent further use
        LICENSE_MANAGER.corrupt_trial()
        sys.exit(1)

    # Show trial information on first run
    remaining_days = LICENSE_MANAGER.get_remaining_days()
    if remaining_days < 7:  # Not first run
        show_trial_info()

    while True:
        clear_screen()

        # Show trial banner
        remaining_days = LICENSE_MANAGER.get_remaining_days()
        days_text = f"{remaining_days:.1f}" if remaining_days < 1 else f"{int(remaining_days)}"
        print_header("Process Activity Monitor", f"TRIAL VERSION - {days_text} DAYS REMAINING")

        options = [
            ("1", "Start Monitoring"),
            ("2", "Display Last Log"),
            ("3", "Export Report"),
            ("4", "Change Configuration"),
            ("5", "Trial Information"),
            ("q", "Exit")
        ]

        print_menu("Select an Option", options)

        choice = Prompt.ask(
            "Select an option",
            choices=["1", "2", "3", "4", "5", "q", "Q"],
            default="q"
        )

        if choice.lower() == 'q':
            print_info("Exiting Process Activity Monitor...")
            break

        if choice == '1':
            start_monitoring()
        elif choice == '2':
            display_last_log()
        elif choice == '3':
            export_report()
        elif choice == '4':
            edit_config()
        elif choice == '5':
            show_trial_info()

if __name__ == "__main__":
    main()