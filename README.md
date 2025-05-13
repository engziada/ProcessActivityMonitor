# Process Activity Monitor

A Python application that monitors user activity (mouse and keyboard) for specified processes and logs their active sessions. The application includes a trial license system and code protection for secure distribution.

## Features

- Monitors specified processes for user activity
- Tracks active sessions with start/end times
- Detects inactivity periods
- Maintains process uptime statistics
- SQLite database storage
- Interactive main menu interface with Rich text formatting
- Real-time monitoring display with timer
- Export reports to Excel and PDF
- Configuration editor
- 7-day trial license system with hardware binding
- Code protection using PyArmor for secure distribution
- Time format standardization (HH:MM:SS)

## Configuration

The application uses `config.ini` for settings:

```ini
[ProcessWatchdog]
# Comma-separated list of process names to monitor
target_processes = Notepad.exe, Ssms.exe, vivaldi.exe
# How often to check for process activity (seconds)
poll_interval = 1.0
# Time without activity before considering session inactive (seconds)
inactivity_timeout = 5.0

[Export]
# Directory to save exported reports (Excel, PDF)
export_directory = ./

[Appearance]
# Color theme for the application
primary_color = blue
accent_color = green
warning_color = red
```

You can edit these settings directly in the file or use the built-in configuration editor from the main menu.

## Database Structure

### MonitoredProcess Table
- `id`: Primary key
- `process_name`: Name of the monitored process (e.g., "notepad.exe")
- `pid`: Process ID
- `last_seen`: Timestamp of last detection
- `last_uptime_seconds`: Total process runtime

### ProcessActivityLog Table
- `id`: Primary key
- `process_id`: Foreign key to MonitoredProcess
- `start_time`: Session start timestamp
- `end_time`: Session end timestamp
- `last_activity_time`: Last detected activity
- `session_uptime_seconds`: Session duration

## How It Works

### Session Management
1. A new session starts when:
   - Process is first detected
   - Activity resumes after inactivity period
   - Process PID changes

2. A session ends when:
   - No activity detected for `inactivity_timeout` seconds (default: 5s)
   - Process terminates
   - Different PID detected for same process

### Timestamps and Durations Explained
- `Last Seen`: Most recent process detection, updated whenever the process is found active
- `Last Activity`: Most recent user interaction (mouse/keyboard) with the process
- `Session Start`: When current activity session began
- `Session End`: When session was terminated
- `Last Uptime`: Total process runtime since process started (independent of sessions)
- `Session Duration`: Time between `Session End` and `Session Start`

Example with correct calculations:
```
Process: notepad.exe (PID: 28016)
Last Seen: 2025-03-18 00:17:17.831549
Last Uptime: 1:28:36
Session Start: 2025-03-18 00:17:17.808482
Last Activity: 2025-03-18 00:17:17.831549
Session End: 2025-03-18 00:18:56.899123
Session Duration: 0:01:39.090641  # Correct calculation: Session End - Session Start
```

## Session Duration Calculation

The session duration is always calculated as:
```python
session_duration = session_end_time - session_start_time
```

For example:
- Session Start: 00:17:17.808482
- Session End: 00:18:56.899123
- Duration: 00:18:56.899123 - 00:17:17.808482 = 1 minute, 39.090641 seconds

## Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure processes to monitor in `config.ini`

3. Run the application:

```bash
python run.py
```

4. Use the main menu to:
   - Start monitoring processes
   - View activity logs
   - Export reports to Excel or PDF
   - Edit configuration settings
   - View trial information

5. Build an executable (optional):

```bash
python build.py
```

Options:
- `--clean` - Clean build files before building (default: True)
- `--no-obfuscate` - Skip code obfuscation step (default: False)

## Requirements

- Python 3.6+
- pynput
- psutil
- SQLAlchemy
- rich
- openpyxl
- reportlab
- cryptography (optional, for enhanced encryption)
- requests (optional, for online time verification)

### Build Requirements

- PyArmor
- PyInstaller

## Trial License System

The application includes a 7-day trial license system with the following features:

- **7-day trial period** from first execution
- **Hardware binding** to prevent copying to other machines
- **Clock manipulation protection** using online time verification
- **Multiple storage locations** for redundancy (file and registry)
- **Automatic corruption** of expired trials
- **Performance optimizations** with caching to reduce system impact

### Trial User Experience

- Users see remaining trial days in the application header
- A dedicated "Trial Information" menu option provides details
- When the trial expires, users are informed and the application exits
- The trial is protected against common bypass methods

## Code Protection

The executable is protected using:

- **PyArmor** for code obfuscation
- **PyInstaller** for creating a standalone executable

### About the .spec File

The `ProcessActivityMonitor.spec` file contains the PyInstaller configuration for building the executable. It includes:

- All required Python modules in the `hiddenimports` list
- All required data files in the `datas` list
- Search paths for modules in the `pathex` list
- Console mode setting (`console=True`) for input functionality

If you add new dependencies or files to the project, update the spec file accordingly.

### Troubleshooting Build Issues

If you encounter "No module named X" errors when running the executable:
1. Add the missing module to the `hiddenimports` list in the spec file
2. Rebuild the executable

If you encounter input-related errors, make sure the application is running in console mode (`console=True` in the spec file)

## Notes

- The application creates a new session after 5 seconds of inactivity
- Multiple sessions can exist for the same process
- Process uptime is tracked independently of activity sessions
- All timestamps are stored in UTC
- All duration values are formatted as HH:MM:SS for consistency