"""
Configuration editor for the Process Activity Monitor.
"""
import os
import configparser
from console_utils import (
    console, print_header, print_info, print_success, 
    print_warning, print_error, clear_screen
)
from rich.prompt import Prompt, Confirm

CONFIG_FILE = 'config.ini'

def load_config():
    """Load the configuration from the config file."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def save_config(config):
    """Save the configuration to the config file."""
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    print_success(f"Configuration saved to {CONFIG_FILE}")

def edit_process_list(config):
    """Edit the list of processes to monitor."""
    current_processes = config['ProcessWatchdog']['target_processes']
    print_info(f"Current processes: {current_processes}")
    
    # Get new process list
    new_processes = Prompt.ask(
        "Enter comma-separated list of processes to monitor",
        default=current_processes
    )
    
    # Update config
    config['ProcessWatchdog']['target_processes'] = new_processes
    save_config(config)

def edit_poll_interval(config):
    """Edit the poll interval."""
    current_interval = config['ProcessWatchdog']['poll_interval']
    print_info(f"Current poll interval: {current_interval} seconds")
    
    # Get new interval
    while True:
        try:
            new_interval = Prompt.ask(
                "Enter new poll interval in seconds",
                default=current_interval
            )
            # Validate input
            float_val = float(new_interval)
            if float_val <= 0:
                print_warning("Poll interval must be greater than 0")
                continue
            break
        except ValueError:
            print_error("Please enter a valid number")
    
    # Update config
    config['ProcessWatchdog']['poll_interval'] = new_interval
    save_config(config)

def edit_inactivity_timeout(config):
    """Edit the inactivity timeout."""
    current_timeout = config['ProcessWatchdog']['inactivity_timeout']
    print_info(f"Current inactivity timeout: {current_timeout} seconds")
    
    # Get new timeout
    while True:
        try:
            new_timeout = Prompt.ask(
                "Enter new inactivity timeout in seconds",
                default=current_timeout
            )
            # Validate input
            float_val = float(new_timeout)
            if float_val <= 0:
                print_warning("Inactivity timeout must be greater than 0")
                continue
            break
        except ValueError:
            print_error("Please enter a valid number")
    
    # Update config
    config['ProcessWatchdog']['inactivity_timeout'] = new_timeout
    save_config(config)

def edit_export_directory(config):
    """Edit the export directory."""
    current_dir = config['Export']['export_directory']
    print_info(f"Current export directory: {current_dir}")
    
    # Get new directory
    new_dir = Prompt.ask(
        "Enter new export directory path",
        default=current_dir
    )
    
    # Validate directory
    if not os.path.exists(new_dir):
        create_dir = Confirm.ask(f"Directory {new_dir} does not exist. Create it?")
        if create_dir:
            try:
                os.makedirs(new_dir, exist_ok=True)
            except Exception as e:
                print_error(f"Failed to create directory: {e}")
                return
        else:
            print_warning("Directory not changed")
            return
    
    # Update config
    config['Export']['export_directory'] = new_dir
    save_config(config)

def edit_config():
    """Main function to edit the configuration."""
    config = load_config()
    
    while True:
        clear_screen()
        print_header("Configuration Editor", "Process Activity Monitor")
        
        console.print("[bold]Current Configuration:[/bold]")
        console.print(f"1. Target Processes: {config['ProcessWatchdog']['target_processes']}")
        console.print(f"2. Poll Interval: {config['ProcessWatchdog']['poll_interval']} seconds")
        console.print(f"3. Inactivity Timeout: {config['ProcessWatchdog']['inactivity_timeout']} seconds")
        console.print(f"4. Export Directory: {config['Export']['export_directory']}")
        console.print()
        
        choice = Prompt.ask(
            "Select option to edit (or 'q' to quit)",
            choices=["1", "2", "3", "4", "q", "Q"],
            default="q"
        )
        
        if choice.lower() == 'q':
            break
        
        if choice == '1':
            edit_process_list(config)
        elif choice == '2':
            edit_poll_interval(config)
        elif choice == '3':
            edit_inactivity_timeout(config)
        elif choice == '4':
            edit_export_directory(config)
        
        # Reload config after changes
        config = load_config()
        
        # Prompt to continue
        console.print()
        Prompt.ask("Press Enter to continue")

if __name__ == "__main__":
    edit_config()
