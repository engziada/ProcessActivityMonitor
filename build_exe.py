"""
Build script to create an obfuscated executable for the Process Activity Monitor.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from console_utils import print_header, print_info, print_success, print_warning, print_error

def check_requirements():
    """Check if required packages are installed."""
    # List of required packages
    required_packages = [
        "PyInstaller",
        "pyarmor",
        "pynput",
        "psutil",
        "pywin32",
        "keyboard",
        "rich",
        "sqlalchemy",
    ]

    missing_packages = []

    # Check each package
    for package in required_packages:
        try:
            __import__(package.lower().replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    # Handle PyInstaller separately (special import name)
    if "PyInstaller" in missing_packages:
        try:
            import PyInstaller
            missing_packages.remove("PyInstaller")
            print_success("PyInstaller is installed")
        except ImportError:
            print_error("PyInstaller is not installed. Please install it with: pip install pyinstaller")

    # Handle pywin32 separately (special import name)
    if "pywin32" in missing_packages:
        try:
            import win32gui
            import win32process
            missing_packages.remove("pywin32")
            print_success("pywin32 is installed")
        except ImportError:
            print_error("pywin32 is not installed. Please install it with: pip install pywin32")

    # Print status for other packages
    for package in required_packages:
        if package not in missing_packages and package not in ["PyInstaller", "pywin32"]:
            print_success(f"{package} is installed")

    # Install missing packages
    if missing_packages:
        print_warning(f"Missing packages: {', '.join(missing_packages)}")
        install = input("Do you want to install missing packages now? (y/n): ")
        if install.lower() == 'y':
            for package in missing_packages:
                try:
                    print_info(f"Installing {package}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    print_success(f"{package} installed successfully")
                except subprocess.CalledProcessError:
                    print_error(f"Failed to install {package}")
                    return False
        else:
            print_warning("Continuing without installing missing packages (may cause build errors)")

    return len(missing_packages) == 0 or install.lower() == 'y'

def obfuscate_code():
    """Obfuscate the Python code using PyArmor."""
    print_info("Obfuscating code with PyArmor...")

    # Check Python version compatibility
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 11:
        print_warning(f"You're using Python {python_version.major}.{python_version.minor}, but PyArmor may have compatibility issues with Python 3.11+")
        print_warning("The 'Python 3.11+ is not supported now' warnings are expected and can be ignored if obfuscation succeeds")
        print_warning("For full compatibility, consider using Python 3.10 or earlier for obfuscation")

        continue_anyway = input("Do you want to continue with obfuscation anyway? (y/n): ")
        if continue_anyway.lower() != 'y':
            print_info("Skipping obfuscation as requested")
            return False

    try:
        # Create a directory for obfuscated files
        obf_dir = Path("obfuscated")
        if obf_dir.exists():
            shutil.rmtree(obf_dir)
        obf_dir.mkdir()

        # List of files to obfuscate
        files_to_obfuscate = [
            "run.py",
            "models.py",
            "console_utils.py",
            "export_utils.py",
            "config_editor.py",
            "query_logs.py",
            "trial_license_manager.py"
        ]

        # Copy config.ini to obfuscated directory
        shutil.copy("config.ini", obf_dir / "config.ini")

        # Track obfuscation success
        obfuscation_success = False

        # Get PyArmor version to determine command structure
        try:
            result = subprocess.run(["pip", "show", "pyarmor"], capture_output=True, text=True)
            if 'Version: ' in result.stdout:
                version = result.stdout.split('Version: ')[1].split('\n')[0]
                print_info(f"PyArmor version: {version}")
                is_pyarmor_8_or_higher = version.startswith('8') or version.startswith('9')
            else:
                print_info("PyArmor version: Unknown")
                is_pyarmor_8_or_higher = False
        except Exception:
            print_warning("Could not determine PyArmor version")
            is_pyarmor_8_or_higher = False

        # Use a simpler approach with pyarmor directly
        for file in files_to_obfuscate:
            if os.path.exists(file):
                obfuscation_success_for_file = False

                # For PyArmor 8.x/9.x, use the 'gen' command
                if is_pyarmor_8_or_higher:
                    try:
                        cmd = [
                            "pyarmor", "gen",
                            "--output", str(obf_dir),
                            file
                        ]
                        subprocess.check_call(cmd)
                        print_success(f"Obfuscated {file}")
                        obfuscation_success = True
                        obfuscation_success_for_file = True
                    except subprocess.CalledProcessError:
                        print_warning(f"Failed to obfuscate {file} with PyArmor 8.x/9.x gen command")

                # If PyArmor 8.x/9.x failed or not available, try with pyarmor-7
                if not obfuscation_success_for_file:
                    try:
                        cmd = [
                            "pyarmor-7", "obfuscate",
                            "--output", str(obf_dir),
                            "--exact",  # Only obfuscate the specified file
                            file
                        ]
                        subprocess.check_call(cmd)
                        print_success(f"Obfuscated {file} with pyarmor-7")
                        obfuscation_success = True
                        obfuscation_success_for_file = True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print_warning(f"Failed to obfuscate {file} with pyarmor-7")

                # If both methods failed, just copy the file
                if not obfuscation_success_for_file:
                    print_warning(f"Failed to obfuscate {file}, copying instead")
                    shutil.copy(file, obf_dir)
            else:
                print_warning(f"File {file} not found, skipping")

        if obfuscation_success:
            print_success("Code obfuscation completed")
            return True
        else:
            print_warning("No files were successfully obfuscated, using unprotected files instead")
            return False
    except Exception as e:
        print_error(f"Error during obfuscation: {e}")
        return False

def build_executable():
    """Build the executable using PyInstaller."""
    print_info("Building executable with PyInstaller...")

    try:
        # Determine if we're using obfuscated code
        source_dir = "obfuscated" if Path("obfuscated").exists() and Path("obfuscated/run.py").exists() else "."
        main_script = os.path.join(source_dir, "run.py")

        # Verify the main script exists
        if not os.path.exists(main_script):
            print_error(f"Main script {main_script} not found")
            return False

        # Verify config.ini exists in the source directory
        config_path = os.path.join(source_dir, "config.ini")
        if not os.path.exists(config_path):
            print_warning(f"Config file not found in {source_dir}, copying from root")
            shutil.copy("config.ini", config_path)

        # PyInstaller command
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name=ProcessActivityMonitor",
            "--onefile",  # Create a single executable
            "--windowed",  # Windows-specific: don't show console window
            "--icon=NONE",  # Add an icon if you have one
            "--add-data", f"{config_path};.",  # Include config file
            # Explicitly include required modules
            "--hidden-import=pynput",
            "--hidden-import=pynput.keyboard",
            "--hidden-import=pynput.mouse",
            "--hidden-import=psutil",
            "--hidden-import=win32gui",
            "--hidden-import=win32process",
            "--hidden-import=keyboard",
            "--hidden-import=rich",
            "--hidden-import=rich.prompt",
            "--hidden-import=rich.panel",
            "--hidden-import=rich.text",
            "--hidden-import=rich.align",
            "--hidden-import=rich.console",
            "--hidden-import=sqlalchemy",
            "--hidden-import=sqlalchemy.ext.declarative",
            "--hidden-import=sqlalchemy.orm",
            "--hidden-import=configparser",
            "--clean",  # Clean PyInstaller cache
            main_script
        ]

        subprocess.check_call(cmd)
        print_success("Executable built successfully")

        # Copy the executable to the root directory
        exe_path = os.path.join("dist", "ProcessActivityMonitor.exe")
        if os.path.exists(exe_path):
            shutil.copy(exe_path, "ProcessActivityMonitor.exe")
            print_success(f"Executable copied to {os.path.abspath('ProcessActivityMonitor.exe')}")

        return True
    except Exception as e:
        print_error(f"Error building executable: {e}")
        return False

def main():
    """Main function to build the executable."""
    print_header("Process Activity Monitor", "Build Executable")

    if not check_requirements():
        print_error("Missing required packages. Please install them and try again.")
        return

    # Ask if user wants to obfuscate the code
    obfuscate = input("Do you want to obfuscate the code for protection? (y/n): ")
    if obfuscate.lower() == 'y':
        if not obfuscate_code():
            print_warning("Continuing without obfuscation")

    # Build the executable
    if build_executable():
        print_success("Build completed successfully!")
        print_info(f"Executable: {os.path.abspath('ProcessActivityMonitor.exe')}")
    else:
        print_error("Build failed")

if __name__ == "__main__":
    main()
