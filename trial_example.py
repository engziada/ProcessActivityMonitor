"""
Example usage of the Trial License Manager.

This example demonstrates how to integrate the Trial License Manager into your application.
"""
import sys
import datetime
from trial_license_manager import TrialLicenseManager

def main():
    """Main function demonstrating the Trial License Manager."""
    print("Trial License Manager Example")
    print("=============================")
    
    # Create a license manager with a 7-day trial period
    license_manager = TrialLicenseManager(
        app_name="ExampleApp",
        trial_days=7,
        enable_online_verification=True
    )
    
    # Check if trial is valid
    if license_manager.is_trial_valid():
        # Trial is valid, continue with application
        remaining_days = license_manager.get_remaining_days()
        expiration_date = license_manager.get_expiration_date()
        
        print(f"Trial is valid!")
        print(f"Remaining days: {remaining_days:.1f}")
        print(f"Expiration date: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Simulate application functionality
        print("\nApplication is running...")
        print("Press Ctrl+C to exit")
        
        try:
            while True:
                # Your application code here
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nApplication closed by user")
    else:
        # Trial has expired, exit application
        print("Trial has expired or been corrupted.")
        print("Please purchase a license to continue using this application.")
        sys.exit(1)

if __name__ == "__main__":
    main()
