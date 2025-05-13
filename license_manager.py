"""
License manager for Process Activity Monitor.
Handles trial period verification and protection against tampering.
"""
import os
import sys
import time
import json
import uuid
import random
import hashlib
import winreg
import sqlite3
import datetime
import requests
import platform
from pathlib import Path
import subprocess
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Constants
TRIAL_DAYS = 7
LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".process_monitor_license")
REGISTRY_KEY = r"Software\ProcessActivityMonitor"
REGISTRY_VALUE = "InstallationData"
ONLINE_TIME_APIS = [
    "http://worldtimeapi.org/api/ip",
    "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
    "https://www.timeapi.io/api/Time/current/zone?timeZone=UTC"
]

# Encryption key derivation
def get_machine_id():
    """Get a unique machine identifier that's hard to spoof."""
    # Combine multiple hardware identifiers
    machine_id = ""
    
    # CPU info
    try:
        if platform.system() == "Windows":
            # Get processor ID from registry
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            processor_id = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            machine_id += processor_id
    except:
        pass
    
    # Windows product ID
    try:
        if platform.system() == "Windows":
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_id = winreg.QueryValueEx(key, "ProductId")[0]
            machine_id += product_id
    except:
        pass
    
    # BIOS serial
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("wmic bios get serialnumber", shell=True).decode().strip()
            for line in output.split('\n'):
                if "SerialNumber" not in line:
                    machine_id += line.strip()
                    break
    except:
        pass
    
    # MAC address (first ethernet adapter)
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("getmac /fo csv /nh", shell=True).decode().strip()
            if output:
                mac = output.split(',')[0].strip('"')
                machine_id += mac
    except:
        pass
    
    # Fallback to platform-specific info if we couldn't get hardware IDs
    if not machine_id:
        machine_id = platform.node() + platform.machine() + platform.processor()
    
    # Create a hash of the machine ID
    return hashlib.sha256(machine_id.encode()).hexdigest()

def get_encryption_key():
    """Generate an encryption key based on the machine ID."""
    machine_id = get_machine_id()
    salt = b'ProcessMonitorSalt'  # Fixed salt
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
    return key

# License data handling
def encrypt_data(data):
    """Encrypt the license data."""
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(json.dumps(data).encode())

def decrypt_data(encrypted_data):
    """Decrypt the license data."""
    key = get_encryption_key()
    f = Fernet(key)
    try:
        decrypted_data = f.decrypt(encrypted_data)
        return json.loads(decrypted_data)
    except:
        return None

def get_current_time():
    """Get the current time from multiple sources to prevent clock manipulation."""
    times = []
    
    # Local time
    local_time = datetime.datetime.now().timestamp()
    times.append(local_time)
    
    # Try to get time from online APIs
    for api_url in ONLINE_TIME_APIS:
        try:
            response = requests.get(api_url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                
                # Parse time based on API format
                if "unixtime" in data:  # worldtimeapi.org
                    times.append(float(data["unixtime"]))
                elif "dateTime" in data:  # timeapi.io
                    dt = datetime.datetime.fromisoformat(data["dateTime"].replace("Z", "+00:00"))
                    times.append(dt.timestamp())
        except:
            continue
    
    # If we have online times, use the median to avoid outliers
    if len(times) > 1:
        times.sort()
        if len(times) % 2 == 0:
            return (times[len(times)//2] + times[len(times)//2 - 1]) / 2
        else:
            return times[len(times)//2]
    
    # Fallback to local time if we couldn't get online time
    return local_time

def save_license_data(data):
    """Save license data to multiple locations."""
    encrypted_data = encrypt_data(data)
    
    # Save to file
    try:
        with open(LICENSE_FILE, "wb") as f:
            f.write(encrypted_data)
    except:
        pass
    
    # Save to registry
    try:
        if platform.system() == "Windows":
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_BINARY, encrypted_data)
            winreg.CloseKey(key)
    except:
        pass
    
    # Save to SQLite database in user's home directory
    try:
        db_path = os.path.join(os.path.expanduser("~"), ".config.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value BLOB)")
        cursor.execute("INSERT OR REPLACE INTO config VALUES (?, ?)", 
                      ("process_monitor_license", encrypted_data))
        conn.commit()
        conn.close()
    except:
        pass

def load_license_data():
    """Load license data from multiple locations."""
    data_sources = []
    
    # Try to load from file
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, "rb") as f:
                encrypted_data = f.read()
                data = decrypt_data(encrypted_data)
                if data:
                    data_sources.append(data)
    except:
        pass
    
    # Try to load from registry
    try:
        if platform.system() == "Windows":
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            encrypted_data = winreg.QueryValueEx(key, REGISTRY_VALUE)[0]
            winreg.CloseKey(key)
            data = decrypt_data(encrypted_data)
            if data:
                data_sources.append(data)
    except:
        pass
    
    # Try to load from SQLite database
    try:
        db_path = os.path.join(os.path.expanduser("~"), ".config.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key=?", ("process_monitor_license",))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                encrypted_data = result[0]
                data = decrypt_data(encrypted_data)
                if data:
                    data_sources.append(data)
    except:
        pass
    
    # If we have multiple sources, use the most restrictive one
    if data_sources:
        # Sort by installation time (oldest first)
        data_sources.sort(key=lambda x: x.get("installation_time", 0))
        return data_sources[0]
    
    return None

# Trial management
def initialize_trial():
    """Initialize the trial period."""
    current_time = get_current_time()
    
    license_data = {
        "installation_time": current_time,
        "expiration_time": current_time + (TRIAL_DAYS * 24 * 60 * 60),
        "machine_id": get_machine_id(),
        "trial_used": True,
        "trial_corrupted": False
    }
    
    save_license_data(license_data)
    return license_data

def check_trial_status():
    """Check if the trial is still valid."""
    license_data = load_license_data()
    
    # If no license data, initialize trial
    if not license_data:
        return initialize_trial()
    
    # Verify machine ID to prevent copying license data
    if license_data.get("machine_id") != get_machine_id():
        license_data["trial_corrupted"] = True
        save_license_data(license_data)
        return license_data
    
    # Get current time
    current_time = get_current_time()
    
    # Check if trial has expired
    if current_time > license_data.get("expiration_time", 0):
        license_data["trial_corrupted"] = True
        save_license_data(license_data)
    
    return license_data

def get_remaining_days():
    """Get the number of days remaining in the trial."""
    license_data = check_trial_status()
    
    if license_data.get("trial_corrupted", False):
        return 0
    
    current_time = get_current_time()
    expiration_time = license_data.get("expiration_time", 0)
    
    remaining_seconds = max(0, expiration_time - current_time)
    remaining_days = remaining_seconds / (24 * 60 * 60)
    
    return remaining_days

def corrupt_trial():
    """Corrupt the trial data to prevent further use."""
    license_data = load_license_data() or {}
    license_data["trial_corrupted"] = True
    license_data["expiration_time"] = 0
    save_license_data(license_data)

def is_trial_valid():
    """Check if the trial is valid and not corrupted."""
    license_data = check_trial_status()
    
    if license_data.get("trial_corrupted", False):
        return False
    
    current_time = get_current_time()
    expiration_time = license_data.get("expiration_time", 0)
    
    return current_time <= expiration_time
