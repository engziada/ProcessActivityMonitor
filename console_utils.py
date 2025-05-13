"""
Console utilities for beautifying the terminal output.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich import box
from datetime import datetime, timedelta
import time
import os
import keyboard
import threading

# Initialize Rich console
console = Console()

# Color constants
COLOR_PRIMARY = "cyan"
COLOR_SECONDARY = "green"
COLOR_ACCENT = "yellow"
COLOR_WARNING = "red"
COLOR_INFO = "blue"

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title, subtitle=None):
    """Print a styled header with optional subtitle."""
    clear_screen()
    console.print()
    text = Text(title, style=f"bold {COLOR_PRIMARY}")
    if subtitle:
        text.append(f"\n{subtitle}", style=COLOR_SECONDARY)
    console.print(Align.center(Panel(text, box=box.DOUBLE, expand=False, padding=(1, 10))))
    console.print()

def print_menu(title, options, footer=None):
    """
    Print a styled menu with options.
    
    Args:
        title (str): The menu title
        options (list): List of (key, description) tuples
        footer (str, optional): Optional footer text
    """
    print_header(title)
    
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Key", style=f"bold {COLOR_ACCENT}")
    table.add_column("Description")
    
    for key, description in options:
        table.add_row(f"[{key}]", description)
    
    console.print(Align.center(table))
    console.print()
    
    if footer:
        console.print(Align.center(Text(footer, style="italic")))
        console.print()

def print_info(message):
    """Print an info message."""
    console.print(f"[{COLOR_INFO}]ℹ {message}[/{COLOR_INFO}]")

def print_success(message):
    """Print a success message."""
    console.print(f"[{COLOR_SECONDARY}]✓ {message}[/{COLOR_SECONDARY}]")

def print_warning(message):
    """Print a warning message."""
    console.print(f"[{COLOR_WARNING}]⚠ {message}[/{COLOR_WARNING}]")

def print_error(message):
    """Print an error message."""
    console.print(f"[bold {COLOR_WARNING}]✗ {message}[/bold {COLOR_WARNING}]")

def format_time_delta(seconds):
    """Format seconds into HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class MonitoringDisplay:
    """Class to handle the live monitoring display."""
    
    def __init__(self, process_monitors, start_time):
        """
        Initialize the monitoring display.
        
        Args:
            process_monitors (dict): Dictionary of process monitors
            start_time (float): Timestamp when monitoring started
        """
        self.process_monitors = process_monitors
        self.start_time = start_time
        self.running = False
        self.live = None
        self.stop_event = threading.Event()
        
    def generate_layout(self):
        """Generate the layout for the monitoring display."""
        layout = Layout()
        
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        elapsed_str = format_time_delta(elapsed)
        
        # Create header
        header_text = Text("PROCESS ACTIVITY MONITOR", style=f"bold {COLOR_PRIMARY}")
        header = Panel(
            Align.center(header_text),
            box=box.DOUBLE,
            style=COLOR_PRIMARY
        )
        
        # Create timer panel
        timer_text = Text(f"Monitoring Time: {elapsed_str}", style=f"bold {COLOR_ACCENT}")
        timer = Panel(
            Align.center(timer_text),
            box=box.SIMPLE,
            style=COLOR_ACCENT
        )
        
        # Create process table
        table = Table(title="Monitored Processes", box=box.SIMPLE)
        table.add_column("Process", style=COLOR_SECONDARY)
        table.add_column("PID", style=COLOR_INFO)
        table.add_column("Status", style=COLOR_PRIMARY)
        table.add_column("Last Activity", style=COLOR_ACCENT)
        
        for name, monitor in self.process_monitors.items():
            status = "Active" if not monitor.is_inactive else "Inactive"
            status_style = COLOR_SECONDARY if not monitor.is_inactive else COLOR_WARNING
            
            pid = str(monitor.pid) if monitor.pid else "N/A"
            
            last_activity = "Never"
            if monitor.current_activity_log and monitor.current_activity_log.last_activity_time:
                last_activity = monitor.current_activity_log.last_activity_time.strftime("%H:%M:%S")
            
            table.add_row(
                name,
                pid,
                f"[{status_style}]{status}[/{status_style}]",
                last_activity
            )
        
        # Create footer with instructions
        footer_text = Text("Press [Ctrl+Q] to stop monitoring and return to main menu", 
                          style=f"italic {COLOR_INFO}")
        footer = Panel(
            Align.center(footer_text),
            box=box.SIMPLE,
            style=COLOR_INFO
        )
        
        # Arrange layout
        layout.split(
            Layout(header, size=3),
            Layout(timer, size=3),
            Layout(table, size=10),
            Layout(footer, size=3)
        )
        
        return layout
    
    def update_display(self):
        """Update the monitoring display."""
        if self.live:
            self.live.update(self.generate_layout())
    
    def start(self):
        """Start the live display."""
        self.running = True
        self.live = Live(self.generate_layout(), refresh_per_second=1)
        self.live.start()
        
        # Start a thread to update the display
        threading.Thread(target=self._update_thread, daemon=True).start()
        
        # Register keyboard shortcut
        keyboard.add_hotkey('ctrl+q', self.stop)
    
    def _update_thread(self):
        """Thread to update the display periodically."""
        while self.running and not self.stop_event.is_set():
            self.update_display()
            time.sleep(1)
    
    def stop(self):
        """Stop the live display."""
        self.running = False
        self.stop_event.set()
        if self.live:
            self.live.stop()
        
        # Remove keyboard shortcut
        keyboard.remove_hotkey('ctrl+q')
