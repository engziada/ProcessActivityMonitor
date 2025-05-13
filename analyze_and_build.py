"""
Analyze Python code to find all imports and build a complete PyInstaller spec file.
"""
import os
import sys
import re
import subprocess
import importlib
import pkgutil
from pathlib import Path
from console_utils import print_header, print_info, print_success, print_warning, print_error

def find_imports_in_file(file_path):
    """Find all import statements in a Python file."""
    imports = set()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find standard imports (import x, import x.y)
    for match in re.finditer(r'import\s+([\w\.]+)(?:\s+as\s+\w+)?', content):
        imports.add(match.group(1))
    
    # Find from imports (from x import y)
    for match in re.finditer(r'from\s+([\w\.]+)\s+import\s+', content):
        imports.add(match.group(1))
    
    return imports

def find_all_imports(directory):
    """Find all imports in all Python files in a directory."""
    all_imports = set()
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    imports = find_imports_in_file(file_path)
                    all_imports.update(imports)
                except Exception as e:
                    print_warning(f"Error processing {file_path}: {e}")
    
    return all_imports

def get_all_submodules(package_name):
    """Get all submodules of a package."""
    try:
        package = importlib.import_module(package_name)
        if not hasattr(package, '__path__'):
            return [package_name]  # Not a package, just a module
        
        submodules = set([package_name])
        
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package_name + '.'):
            submodules.add(name)
            if is_pkg:
                submodules.update(get_all_submodules(name))
        
        return submodules
    except ImportError:
        return [package_name]  # Can't import, just return the name

def create_spec_file(imports, source_dir, output_name):
    """Create a PyInstaller spec file with all necessary imports."""
    # Get all Python files in the source directory
    python_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.py') or file.endswith('.ini'):
                rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(source_dir))
                python_files.append(rel_path)
    
    # Create datas list for all Python files
    datas = []
    for file in python_files:
        datas.append(f"('{file}', '.')")
    
    # Create hiddenimports list
    hiddenimports = []
    for imp in imports:
        # Skip standard library modules
        if imp in sys.builtin_module_names or imp.startswith('_'):
            continue
        
        # Add the base module
        hiddenimports.append(f"'{imp}'")
        
        # Try to get submodules
        try:
            submodules = get_all_submodules(imp)
            for submodule in submodules:
                if submodule != imp:
                    hiddenimports.append(f"'{submodule}'")
        except Exception as e:
            print_warning(f"Error getting submodules for {imp}: {e}")
    
    # Create the spec file content
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{os.path.join(source_dir, "run.py")}'],
    pathex=['{source_dir}'],
    binaries=[],
    datas=[
        {',\\n        '.join(datas)}
    ],
    hiddenimports=[
        {',\\n        '.join(hiddenimports)}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='{output_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
"""
    
    # Write the spec file
    spec_file = f"{output_name}.spec"
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print_success(f"Created spec file: {spec_file}")
    return spec_file

def build_executable(spec_file):
    """Build the executable using PyInstaller."""
    print_info("Building executable with PyInstaller...")
    
    try:
        subprocess.check_call([sys.executable, '-m', 'PyInstaller', spec_file, '--clean'])
        print_success("Executable built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error building executable: {e}")
        return False

def main():
    """Main function."""
    print_header("PyInstaller Dependency Analyzer", "Build Complete Executable")
    
    # Ask for source directory
    source_dir = input("Enter source directory (default: obfuscated): ").strip() or "obfuscated"
    if not os.path.exists(source_dir):
        print_error(f"Directory not found: {source_dir}")
        return
    
    # Ask for output name
    output_name = input("Enter output name (default: ProcessActivityMonitor): ").strip() or "ProcessActivityMonitor"
    
    print_info(f"Analyzing imports in {source_dir}...")
    imports = find_all_imports(source_dir)
    
    print_info(f"Found {len(imports)} imports:")
    for imp in sorted(imports):
        print(f"  - {imp}")
    
    # Create spec file
    spec_file = create_spec_file(imports, source_dir, output_name)
    
    # Ask to build
    build = input("Build executable now? (y/n): ").strip().lower()
    if build == 'y':
        if build_executable(spec_file):
            # Copy to root directory
            exe_path = os.path.join("dist", f"{output_name}.exe")
            if os.path.exists(exe_path):
                import shutil
                shutil.copy(exe_path, f"{output_name}.exe")
                print_success(f"Executable copied to {os.path.abspath(f'{output_name}.exe')}")
    
    print_info("Done!")

if __name__ == "__main__":
    main()
