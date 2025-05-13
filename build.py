"""
Build script for Process Activity Monitor.

This script builds the executable using the ProcessActivityMonitor.spec file,
which contains all the necessary configuration for PyInstaller.

Usage:
    python build.py [--clean] [--no-obfuscate]

Options:
    --clean         Clean build files before building (default: True)
    --no-obfuscate  Skip code obfuscation step (default: False)
"""
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from console_utils import print_header, print_info, print_success, print_warning, print_error

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Build Process Activity Monitor executable")
    parser.add_argument("--clean", action="store_true", default=True,
                        help="Clean build files before building (default: True)")
    parser.add_argument("--no-obfuscate", action="store_true", default=False,
                        help="Skip code obfuscation step (default: False)")
    return parser.parse_args()

def clean_build_files():
    """Clean up build files and directories."""
    print_info("Cleaning build files...")

    # Directories to remove
    dirs_to_remove = ["build", "dist", "__pycache__", "obfuscated"]

    # Files to remove
    files_to_remove = ["*.pyc", "*.pyo", "*.pyd", "*.spec"]

    # Remove directories
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print_success(f"Removed directory: {dir_name}")
            except Exception as e:
                print_warning(f"Failed to remove {dir_name}: {e}")

    # Remove files (except our spec file)
    for pattern in files_to_remove:
        if pattern == "*.spec":
            # Keep our spec file
            for file in Path(".").glob(pattern):
                if file.name != "ProcessActivityMonitor.spec":
                    try:
                        os.remove(file)
                        print_success(f"Removed file: {file}")
                    except Exception as e:
                        print_warning(f"Failed to remove {file}: {e}")
        else:
            for file in Path(".").glob(pattern):
                try:
                    os.remove(file)
                    print_success(f"Removed file: {file}")
                except Exception as e:
                    print_warning(f"Failed to remove {file}: {e}")

    print_success("Cleanup completed")

def obfuscate_code():
    """Obfuscate the Python code using PyArmor."""
    print_info("Obfuscating code with PyArmor...")

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

        # Obfuscate each file
        obfuscation_success = False
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

def update_spec_file(use_obfuscated=False):
    """Update the spec file to use either original or obfuscated files."""
    print_info(f"Updating spec file to use {'obfuscated' if use_obfuscated else 'original'} files...")

    try:
        spec_file = "ProcessActivityMonitor.spec"
        if not os.path.exists(spec_file):
            print_error(f"Spec file not found: {spec_file}")
            return False

        with open(spec_file, 'r') as f:
            content = f.read()

        if use_obfuscated:
            # Update to use obfuscated files
            content = content.replace(
                "a = Analysis(\n    ['run.py'],\n    pathex=['.'],",
                "a = Analysis(\n    ['obfuscated\\\\run.py'],\n    pathex=['obfuscated'],")

            # Update datas section to include obfuscated files
            content = content.replace(
                "datas=[\n        ('config.ini', '.'),\n    ],",
                "datas=[\n        ('obfuscated\\\\config.ini', '.'),\n    ],")
        else:
            # Update to use original files
            content = content.replace(
                "a = Analysis(\n    ['obfuscated\\\\run.py'],\n    pathex=['obfuscated'],",
                "a = Analysis(\n    ['run.py'],\n    pathex=['.'],")

            # Update datas section to include original files
            content = content.replace(
                "datas=[\n        ('obfuscated\\\\config.ini', '.'),\n    ],",
                "datas=[\n        ('config.ini', '.'),\n    ],")

        with open(spec_file, 'w') as f:
            f.write(content)

        print_success(f"Spec file updated to use {'obfuscated' if use_obfuscated else 'original'} files")
        return True
    except Exception as e:
        print_error(f"Error updating spec file: {e}")
        return False

def build_executable(use_obfuscated=False):
    """Build the executable using PyInstaller."""
    print_info("Building executable with PyInstaller...")

    try:
        # Check if spec file exists
        spec_file = "ProcessActivityMonitor.spec"
        if not os.path.exists(spec_file):
            print_error(f"Spec file not found: {spec_file}")
            return False

        # Update spec file to use obfuscated or original files
        if not update_spec_file(use_obfuscated):
            return False

        # Build using the spec file
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            spec_file,
            "--clean"
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
    args = parse_args()

    print_header("Process Activity Monitor", "Build Executable")

    # Clean build files if requested
    if args.clean:
        clean_build_files()

    # Obfuscate code if requested
    obfuscated = False
    if not args.no_obfuscate:
        obfuscated = obfuscate_code()

    # Build the executable
    if build_executable(use_obfuscated=obfuscated):
        print_success("Build completed successfully!")
        print_info(f"Executable: {os.path.abspath('ProcessActivityMonitor.exe')}")
        print_info(f"Code protection: {'Obfuscated with PyArmor' if obfuscated else 'Not obfuscated'}")
    else:
        print_error("Build failed")

if __name__ == "__main__":
    main()
