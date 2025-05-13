"""
Trial License Manager - A reusable module for implementing trial functionality in Python applications.

Features:
- Configurable trial period
- Protection against clock manipulation
- Multiple storage locations for license data
- Hardware binding to prevent copying
- Automatic corruption of expired trials
- Online time verification (optional)

Usage:
    from trial_license_manager import TrialLicenseManager

    # Create a license manager with default settings (7-day trial)
    license_manager = TrialLicenseManager(
        app_name="MyApplication",
        trial_days=7,
        enable_online_verification=True
    )

    # Check if trial is valid
    if license_manager.is_trial_valid():
        # Trial is valid, continue with application
        remaining_days = license_manager.get_remaining_days()
        print(f"You have {remaining_days:.1f} days remaining in your trial.")
    else:
        # Trial has expired, exit application
        print("Your trial has expired.")
        sys.exit(1)
"""
import os
import sys
import time
import json
import random
import hashlib
import datetime
import platform
from pathlib import Path
import subprocess
import base64
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrialLicenseManager")

# Try to import optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests module not available. Online time verification disabled.")

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False
    logger.warning("winreg module not available. Registry storage disabled.")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography module not available. Using fallback encryption.")

class TrialLicenseManager:
    """
    Trial License Manager for implementing trial functionality in Python applications.
    """

    def __init__(
        self,
        app_name: str,
        trial_days: int = 7,
        enable_online_verification: bool = True,
        license_file_name: Optional[str] = None,
        registry_key: Optional[str] = None,
        salt: Optional[bytes] = None,
        time_apis: Optional[List[str]] = None,
        cache_duration: int = 1800  # Cache duration in seconds (30 minutes)
    ):
        """
        Initialize the Trial License Manager.

        Args:
            app_name: Name of the application (used for storage locations)
            trial_days: Number of days for the trial period
            enable_online_verification: Whether to verify time with online services
            license_file_name: Custom name for the license file
            registry_key: Custom registry key for Windows
            salt: Custom salt for encryption
            time_apis: List of time API URLs for online verification
            cache_duration: How long to cache license status (in seconds)
        """
        self.app_name = app_name
        self.trial_days = trial_days
        self.enable_online_verification = enable_online_verification and REQUESTS_AVAILABLE
        self.cache_duration = cache_duration

        # Set up storage locations
        self.license_file = license_file_name or os.path.join(
            os.path.expanduser("~"), f".{app_name.lower().replace(' ', '_')}_license"
        )
        self.registry_key = registry_key or f"Software\\{app_name.replace(' ', '')}"
        self.registry_value = "LicenseData"
        # Remove database file reference to avoid SQLite journal files
        self.db_file = None

        # Set up encryption
        self.salt = salt or f"{app_name}Salt".encode()

        # Set up time APIs
        self.time_apis = time_apis or [
            "http://worldtimeapi.org/api/ip",
            "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
            "https://www.timeapi.io/api/Time/current/zone?timeZone=UTC"
        ]

        # Cache for license data and status
        self._license_cache = None
        self._cache_time = 0
        self._online_time_offset = 0  # Difference between online and local time
        self._online_time_checked = False

        # Initialize or verify license
        self._check_trial_status(force=True)

    def _get_machine_id(self) -> str:
        """
        Get a unique machine identifier that's hard to spoof.

        Returns:
            A hash string uniquely identifying the machine
        """
        machine_id = ""

        # CPU info
        try:
            if platform.system() == "Windows" and WINREG_AVAILABLE:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                processor_id = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                machine_id += processor_id
        except Exception as e:
            logger.debug(f"Could not get processor ID: {e}")

        # Windows product ID
        try:
            if platform.system() == "Windows" and WINREG_AVAILABLE:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                product_id = winreg.QueryValueEx(key, "ProductId")[0]
                machine_id += product_id
        except Exception as e:
            logger.debug(f"Could not get Windows product ID: {e}")

        # BIOS serial
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic bios get serialnumber", shell=True).decode().strip()
                for line in output.split('\n'):
                    if "SerialNumber" not in line:
                        machine_id += line.strip()
                        break
        except Exception as e:
            logger.debug(f"Could not get BIOS serial: {e}")

        # MAC address (first ethernet adapter)
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("getmac /fo csv /nh", shell=True).decode().strip()
                if output:
                    mac = output.split(',')[0].strip('"')
                    machine_id += mac
        except Exception as e:
            logger.debug(f"Could not get MAC address: {e}")

        # Fallback to platform-specific info if we couldn't get hardware IDs
        if not machine_id:
            machine_id = platform.node() + platform.machine() + platform.processor()

        # Create a hash of the machine ID
        return hashlib.sha256(machine_id.encode()).hexdigest()

    def _get_encryption_key(self) -> bytes:
        """
        Generate an encryption key based on the machine ID.

        Returns:
            Encryption key as bytes
        """
        machine_id = self._get_machine_id()

        if CRYPTOGRAPHY_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
            return key
        else:
            # Fallback encryption if cryptography module is not available
            key = hashlib.sha256(machine_id.encode() + self.salt).digest()
            return base64.urlsafe_b64encode(key)

    def _encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """
        Encrypt the license data.

        Args:
            data: Dictionary of license data

        Returns:
            Encrypted data as bytes
        """
        key = self._get_encryption_key()

        if CRYPTOGRAPHY_AVAILABLE:
            f = Fernet(key)
            return f.encrypt(json.dumps(data).encode())
        else:
            # Fallback encryption
            json_data = json.dumps(data).encode()
            xor_key = key[:len(json_data)] if len(key) >= len(json_data) else key + key * (len(json_data) // len(key) + 1)
            xor_key = xor_key[:len(json_data)]

            # XOR encryption
            encrypted = bytes(a ^ b for a, b in zip(json_data, xor_key))
            return base64.b64encode(encrypted)

    def _decrypt_data(self, encrypted_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Decrypt the license data.

        Args:
            encrypted_data: Encrypted data as bytes

        Returns:
            Decrypted data as dictionary or None if decryption fails
        """
        key = self._get_encryption_key()

        try:
            if CRYPTOGRAPHY_AVAILABLE:
                f = Fernet(key)
                decrypted_data = f.decrypt(encrypted_data)
                return json.loads(decrypted_data)
            else:
                # Fallback decryption
                encrypted = base64.b64decode(encrypted_data)
                xor_key = key[:len(encrypted)] if len(key) >= len(encrypted) else key + key * (len(encrypted) // len(key) + 1)
                xor_key = xor_key[:len(encrypted)]

                # XOR decryption
                decrypted = bytes(a ^ b for a, b in zip(encrypted, xor_key))
                return json.loads(decrypted)
        except Exception as e:
            logger.debug(f"Decryption failed: {e}")
            return None

    def _get_current_time(self, force_online_check: bool = False) -> float:
        """
        Get the current time from multiple sources to prevent clock manipulation.

        Args:
            force_online_check: Whether to force an online time check

        Returns:
            Current time as Unix timestamp
        """
        # Local time
        local_time = datetime.datetime.now().timestamp()

        # If we've already checked online time, apply the offset to local time
        if self._online_time_checked and not force_online_check:
            return local_time + self._online_time_offset

        # Try to get time from online APIs if enabled
        if self.enable_online_verification and REQUESTS_AVAILABLE:
            online_times = []

            # Only try one API at a time to reduce delays
            # Rotate through APIs on subsequent calls
            api_index = int(time.time() / 60) % len(self.time_apis)  # Change API every minute
            api_url = self.time_apis[api_index]

            try:
                response = requests.get(api_url, timeout=1)  # Reduced timeout
                if response.status_code == 200:
                    data = response.json()

                    # Parse time based on API format
                    if "unixtime" in data:  # worldtimeapi.org
                        online_time = float(data["unixtime"])
                        online_times.append(online_time)
                    elif "dateTime" in data:  # timeapi.io
                        dt = datetime.datetime.fromisoformat(data["dateTime"].replace("Z", "+00:00"))
                        online_time = dt.timestamp()
                        online_times.append(online_time)

                    # Calculate and store the offset
                    if online_times:
                        self._online_time_offset = online_times[0] - local_time
                        self._online_time_checked = True
                        return online_times[0]
            except Exception as e:
                logger.debug(f"Failed to get time from {api_url}: {e}")

        # Fallback to local time if we couldn't get online time
        return local_time

    def _save_license_data(self, data: Dict[str, Any]) -> None:
        """
        Save license data to multiple locations.

        Args:
            data: Dictionary of license data
        """
        encrypted_data = self._encrypt_data(data)

        # Update cache
        self._license_cache = data
        self._cache_time = time.time()

        # Primary storage: file
        primary_saved = False
        try:
            with open(self.license_file, "wb") as f:
                f.write(encrypted_data)
            logger.debug(f"License data saved to file: {self.license_file}")
            primary_saved = True
        except Exception as e:
            logger.debug(f"Failed to save license data to file: {e}")

        # If primary storage failed, try registry as backup
        if not primary_saved and platform.system() == "Windows" and WINREG_AVAILABLE:
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.registry_key)
                winreg.SetValueEx(key, self.registry_value, 0, winreg.REG_BINARY, encrypted_data)
                winreg.CloseKey(key)
                logger.debug(f"License data saved to registry: {self.registry_key}")
                primary_saved = True
            except Exception as e:
                logger.debug(f"Failed to save license data to registry: {e}")

        # If both primary methods failed, try registry as last resort
        # Skip database operations entirely to avoid journal files
        if not primary_saved and platform.system() == "Windows" and WINREG_AVAILABLE:
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.registry_key)
                winreg.SetValueEx(key, self.registry_value, 0, winreg.REG_BINARY, encrypted_data)
                winreg.CloseKey(key)
                logger.debug(f"License data saved to registry: {self.registry_key}")
            except Exception as e:
                logger.debug(f"Failed to save license data to registry: {e}")

        # Occasionally update registry for redundancy
        # Do this randomly about 5% of the time to reduce frequency
        if random.random() < 0.05:
            # Try to update registry if not already done
            if primary_saved and platform.system() == "Windows" and WINREG_AVAILABLE:
                try:
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.registry_key)
                    winreg.SetValueEx(key, self.registry_value, 0, winreg.REG_BINARY, encrypted_data)
                    winreg.CloseKey(key)
                except Exception:
                    pass

    def _load_license_data(self) -> Optional[Dict[str, Any]]:
        """
        Load license data from multiple locations.

        Returns:
            License data dictionary or None if not found
        """
        # Check if we have a valid cache
        current_time = time.time()
        if self._license_cache and (current_time - self._cache_time) < self.cache_duration:
            return self._license_cache

        data_sources = []

        # Try to load from file (primary storage)
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, "rb") as f:
                    encrypted_data = f.read()
                    data = self._decrypt_data(encrypted_data)
                    if data:
                        data_sources.append(data)
                        logger.debug(f"License data loaded from file: {self.license_file}")
        except Exception as e:
            logger.debug(f"Failed to load license data from file: {e}")

        # If file failed, try registry
        if not data_sources and platform.system() == "Windows" and WINREG_AVAILABLE:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key)
                encrypted_data = winreg.QueryValueEx(key, self.registry_value)[0]
                winreg.CloseKey(key)
                data = self._decrypt_data(encrypted_data)
                if data:
                    data_sources.append(data)
                    logger.debug(f"License data loaded from registry: {self.registry_key}")
            except Exception as e:
                logger.debug(f"Failed to load license data from registry: {e}")

        # Skip database operations entirely to avoid journal files

        # If we have data, use it and update cache
        if data_sources:
            # Sort by installation time (oldest first)
            data_sources.sort(key=lambda x: x.get("installation_time", 0))
            result = data_sources[0]

            # Update cache
            self._license_cache = result
            self._cache_time = current_time

            return result

        return None

    def _initialize_trial(self) -> Dict[str, Any]:
        """
        Initialize the trial period.

        Returns:
            License data dictionary
        """
        current_time = self._get_current_time()

        license_data = {
            "installation_time": current_time,
            "expiration_time": current_time + (self.trial_days * 24 * 60 * 60),
            "machine_id": self._get_machine_id(),
            "trial_used": True,
            "trial_corrupted": False,
            "app_name": self.app_name
        }

        self._save_license_data(license_data)
        logger.info(f"Trial initialized for {self.app_name}. Expires in {self.trial_days} days.")
        return license_data

    def _check_trial_status(self, force: bool = False) -> Dict[str, Any]:
        """
        Check if the trial is still valid.

        Args:
            force: Whether to force a full check bypassing the cache

        Returns:
            License data dictionary
        """
        # Check if we have a valid cache and not forcing a check
        current_time = time.time()
        if not force and self._license_cache and (current_time - self._cache_time) < self.cache_duration:
            return self._license_cache

        license_data = self._load_license_data()

        # If no license data, initialize trial
        if not license_data:
            return self._initialize_trial()

        # Verify machine ID to prevent copying license data
        if license_data.get("machine_id") != self._get_machine_id():
            license_data["trial_corrupted"] = True
            self._save_license_data(license_data)
            logger.warning("Machine ID mismatch. Trial corrupted.")
            return license_data

        # Verify app name
        if license_data.get("app_name") != self.app_name:
            license_data["trial_corrupted"] = True
            self._save_license_data(license_data)
            logger.warning("App name mismatch. Trial corrupted.")
            return license_data

        # Get current time - only check online time occasionally
        current_time = self._get_current_time(force_online_check=force)

        # Check if trial has expired
        if current_time > license_data.get("expiration_time", 0):
            license_data["trial_corrupted"] = True
            self._save_license_data(license_data)
            logger.info("Trial has expired.")

        # Update cache
        self._license_cache = license_data
        self._cache_time = time.time()

        return license_data

    # Public methods

    def is_trial_valid(self) -> bool:
        """
        Check if the trial is valid and not corrupted.

        Returns:
            True if trial is valid, False otherwise
        """
        license_data = self._check_trial_status()

        if license_data.get("trial_corrupted", False):
            return False

        # Use cached time for better performance
        current_time = time.time() + self._online_time_offset if self._online_time_checked else self._get_current_time()
        expiration_time = license_data.get("expiration_time", 0)

        return current_time <= expiration_time

    def get_remaining_days(self) -> float:
        """
        Get the number of days remaining in the trial.

        Returns:
            Number of days remaining (can be fractional)
        """
        license_data = self._check_trial_status()

        if license_data.get("trial_corrupted", False):
            return 0.0

        # Use cached time for better performance
        current_time = time.time() + self._online_time_offset if self._online_time_checked else self._get_current_time()
        expiration_time = license_data.get("expiration_time", 0)

        remaining_seconds = max(0, expiration_time - current_time)
        remaining_days = remaining_seconds / (24 * 60 * 60)

        return remaining_days

    def get_expiration_date(self) -> Optional[datetime.datetime]:
        """
        Get the expiration date of the trial.

        Returns:
            Expiration date as datetime object or None if trial is corrupted
        """
        license_data = self._check_trial_status()

        if license_data.get("trial_corrupted", False):
            return None

        expiration_time = license_data.get("expiration_time", 0)
        return datetime.datetime.fromtimestamp(expiration_time)

    def corrupt_trial(self) -> None:
        """
        Corrupt the trial data to prevent further use.
        """
        license_data = self._load_license_data() or {}
        license_data["trial_corrupted"] = True
        license_data["expiration_time"] = 0
        self._save_license_data(license_data)
        logger.info("Trial has been corrupted.")

    def reset_trial(self) -> bool:
        """
        Reset the trial period (for development/testing purposes).

        Returns:
            True if reset was successful, False otherwise
        """
        try:
            # Remove license file
            if os.path.exists(self.license_file):
                os.remove(self.license_file)

            # Remove registry key (Windows only)
            if platform.system() == "Windows" and WINREG_AVAILABLE:
                try:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.registry_key)
                except:
                    pass

            # Clear cache
            self._license_cache = None
            self._cache_time = 0
            self._online_time_offset = 0
            self._online_time_checked = False

            # Initialize new trial
            self._initialize_trial()
            logger.info("Trial has been reset.")
            return True
        except Exception as e:
            logger.error(f"Failed to reset trial: {e}")
            return False