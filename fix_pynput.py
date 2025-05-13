"""
Fix script to add pynput to the PyInstaller spec file.
"""
import os
import sys
import re
from pathlib import Path

def print_info(message):
    print(f"\033[94mℹ {message}\033[0m")

def print_success(message):
    print(f"\033[92m✓ {message}\033[0m")

def print_warning(message):
    print(f"\033[93m⚠ {message}\033[0m")

def print_error(message):
    print(f"\033[91mERROR    {message}\033[0m")

def find_spec_file():
    """Find the PyInstaller spec file."""
    spec_file = Path("ProcessActivityMonitor.spec")
    if spec_file.exists():
        return spec_file

    # Look in the current directory for any .spec files
    spec_files = list(Path(".").glob("*.spec"))
    if spec_files:
        return spec_files[0]

    return None

def update_spec_file(spec_file):
    """Update the spec file to include pynput."""
    print_info(f"Updating spec file: {spec_file}")

    with open(spec_file, "r") as f:
        content = f.read()

    # Check if pynput is already included
    if "pynput" in content:
        print_info("pynput is already included in the spec file")

        # Make sure all required modules are included
        required_modules = [
            "pynput", "pynput.keyboard", "pynput.mouse",
            "psutil", "win32gui", "win32process", "keyboard",
            "rich", "rich.prompt", "rich.panel", "rich.text", "rich.align", "rich.console",
            "sqlalchemy", "sqlalchemy.ext.declarative", "sqlalchemy.orm", "configparser"
        ]

        missing_modules = []
        for module in required_modules:
            if module not in content:
                missing_modules.append(module)

        if missing_modules:
            print_warning(f"Missing modules in spec file: {', '.join(missing_modules)}")

            # Add missing modules to hiddenimports
            hiddenimports_match = re.search(r"hiddenimports=\[(.*?)\]", content, re.DOTALL)
            if hiddenimports_match:
                current_imports = hiddenimports_match.group(1).strip()
                # If hiddenimports is empty, don't add a comma
                if not current_imports:
                    new_imports = ", ".join([f"'{module}'" for module in missing_modules])
                else:
                    new_imports = current_imports + ", " + ", ".join([f"'{module}'" for module in missing_modules])

                updated_content = re.sub(
                    r"hiddenimports=\[(.*?)\]",
                    f"hiddenimports=[{new_imports}]",
                    content,
                    flags=re.DOTALL
                )

            with open(spec_file, "w") as f:
                f.write(updated_content)

            print_success("Updated spec file with missing modules")
        else:
            print_success("All required modules are already included")

        return True

    # Add pynput to hiddenimports
    # First, check the current hiddenimports content
    hiddenimports_match = re.search(r"hiddenimports=\[(.*?)\]", content, re.DOTALL)
    if hiddenimports_match:
        current_imports = hiddenimports_match.group(1).strip()
        # If hiddenimports is empty, don't add a comma
        if not current_imports:
            new_imports = "'pynput', 'pynput.keyboard', 'pynput.mouse', 'psutil', 'win32gui', 'win32process', 'keyboard', 'rich', 'rich.prompt', 'rich.panel', 'rich.text', 'rich.align', 'rich.console', 'sqlalchemy', 'sqlalchemy.ext.declarative', 'sqlalchemy.orm', 'configparser'"
        else:
            new_imports = current_imports + ", 'pynput', 'pynput.keyboard', 'pynput.mouse', 'psutil', 'win32gui', 'win32process', 'keyboard', 'rich', 'rich.prompt', 'rich.panel', 'rich.text', 'rich.align', 'rich.console', 'sqlalchemy', 'sqlalchemy.ext.declarative', 'sqlalchemy.orm', 'configparser'"

        updated_content = re.sub(
            r"hiddenimports=\[(.*?)\]",
            f"hiddenimports=[{new_imports}]",
            content,
            flags=re.DOTALL
        )
    else:
        # If hiddenimports not found, add it
        updated_content = content.replace(
            "Analysis(",
            "Analysis(\n    hiddenimports=['pynput', 'pynput.keyboard', 'pynput.mouse', 'psutil', 'win32gui', 'win32process', 'keyboard', 'rich', 'rich.prompt', 'rich.panel', 'rich.text', 'rich.align', 'rich.console', 'sqlalchemy', 'sqlalchemy.ext.declarative', 'sqlalchemy.orm', 'configparser'],",
            1
        )

    with open(spec_file, "w") as f:
        f.write(updated_content)

    print_success("Updated spec file with required modules")
    return True

def rebuild_executable(spec_file):
    """Rebuild the executable using the updated spec file."""
    print_info("Rebuilding executable...")

    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", str(spec_file), "--clean"])
        print_success("Executable rebuilt successfully")

        # Copy the executable to the root directory
        exe_path = os.path.join("dist", spec_file.stem + ".exe")
        if os.path.exists(exe_path):
            import shutil
            shutil.copy(exe_path, spec_file.stem + ".exe")
            print_success(f"Executable copied to {os.path.abspath(spec_file.stem + '.exe')}")

        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error rebuilding executable: {e}")
        return False

def main():
    """Main function."""
    print_info("Fixing pynput issue in PyInstaller spec file")

    spec_file = find_spec_file()
    if not spec_file:
        print_error("No spec file found. Please run the build script first.")
        return

    if update_spec_file(spec_file):
        rebuild_executable(spec_file)

if __name__ == "__main__":
    main()
