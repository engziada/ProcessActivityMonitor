"""
Test script to check PyArmor compatibility with Python 3.11+
"""
import os
import sys
import subprocess
from pathlib import Path

def print_info(message):
    print(f"\033[94mℹ {message}\033[0m")

def print_success(message):
    print(f"\033[92m✓ {message}\033[0m")

def print_warning(message):
    print(f"\033[93m⚠ {message}\033[0m")

def print_error(message):
    print(f"\033[91mERROR    {message}\033[0m")

def main():
    """Test PyArmor with Python 3.11+"""
    print_info(f"Testing PyArmor with Python {sys.version}")

    # Create a test directory
    test_dir = Path("pyarmor_test")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    test_dir.mkdir()

    # Create a simple test file
    test_file = test_dir / "test.py"
    with open(test_file, "w") as f:
        f.write("""
def main():
    print("Hello from obfuscated code!")

if __name__ == "__main__":
    main()
""")

    print_info("Created test file")

    # Try to obfuscate with PyArmor
    print_info("Attempting to obfuscate with PyArmor...")

    try:
        # Get PyArmor version
        result = subprocess.run(["pip", "show", "pyarmor"], capture_output=True, text=True)
        if 'Version: ' in result.stdout:
            version = result.stdout.split('Version: ')[1].split('\n')[0]
            print_info(f"PyArmor version: {version}")
        else:
            print_info("PyArmor version: Unknown")

        # Check PyArmor version to determine command structure
        if version.startswith('8') or version.startswith('9'):
            print_info("Using PyArmor 8.x/9.x command structure")
            # For PyArmor 8.x/9.x, use the 'gen' command
            cmd = ["pyarmor", "gen", "--output", str(test_dir / "dist"), str(test_file)]
        else:
            print_info("Using PyArmor 7.x command structure")
            # For PyArmor 7.x and earlier, use the 'obfuscate' command
            cmd = ["pyarmor", "obfuscate", "--output", str(test_dir / "dist"), str(test_file)]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print_success("Obfuscation successful!")
            print_info("Output from PyArmor:")
            print(result.stdout)

            # Try running the obfuscated file
            # For PyArmor 8.x/9.x, the output structure is different
            if version.startswith('8') or version.startswith('9'):
                obf_file = test_dir / "dist" / "test.py"
            else:
                obf_file = test_dir / "dist" / "test.py"

            if obf_file.exists():
                print_info("Attempting to run obfuscated file...")
                try:
                    result = subprocess.run([sys.executable, str(obf_file)], capture_output=True, text=True)
                    if result.returncode == 0:
                        print_success("Obfuscated file ran successfully!")
                        print_info("Output:")
                        print(result.stdout)
                    else:
                        print_error("Failed to run obfuscated file")
                        print_info("Error output:")
                        print(result.stderr)
                except Exception as e:
                    print_error(f"Error running obfuscated file: {e}")
            else:
                print_error(f"Obfuscated file not found at {obf_file}")

                # List files in the dist directory
                print_info("Files in the dist directory:")
                try:
                    for file in (test_dir / "dist").iterdir():
                        print(f"  - {file.name}")
                except Exception as e:
                    print_error(f"Error listing files: {e}")
        else:
            print_error("Obfuscation failed")
            print_info("Error output:")
            print(result.stderr)
            print_info("Standard output:")
            print(result.stdout)

            # Try with pyarmor-7 if available
            print_info("Attempting with pyarmor-7...")
            try:
                cmd = ["pyarmor-7", "obfuscate", "--output", str(test_dir / "dist"), str(test_file)]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    print_success("Obfuscation with pyarmor-7 successful!")

                    # Try running the obfuscated file
                    obf_file = test_dir / "dist" / "test.py"
                    if obf_file.exists():
                        print_info("Attempting to run obfuscated file...")
                        try:
                            result = subprocess.run([sys.executable, str(obf_file)], capture_output=True, text=True)
                            if result.returncode == 0:
                                print_success("Obfuscated file ran successfully!")
                                print_info("Output:")
                                print(result.stdout)
                            else:
                                print_error("Failed to run obfuscated file")
                                print_info("Error output:")
                                print(result.stderr)
                        except Exception as e:
                            print_error(f"Error running obfuscated file: {e}")
                    else:
                        print_error(f"Obfuscated file not found at {obf_file}")
                else:
                    print_error("Obfuscation with pyarmor-7 failed")
                    print_info("Error output:")
                    print(result.stderr)
            except FileNotFoundError:
                print_warning("pyarmor-7 not found")
    except Exception as e:
        print_error(f"Error during test: {e}")

    print_info("Test completed")

if __name__ == "__main__":
    main()
