#!/usr/bin/env python3
"""
Test script to verify ChromeDriver setup is working
"""

import sys
import os
# Add parent directory to path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.driver_setup import CHROME_PROFILES, managed_driver

def test_driver_setup():
    """Test driver setup for all profiles"""
    print("🧪 Testing ChromeDriver setup for all profiles...")
    
    for i, profile in enumerate(CHROME_PROFILES):
        profile_name = profile['profile_dir']
        print(f"\n📱 Testing Profile: {profile_name}")
        print("-" * 40)
        
        try:
            with managed_driver(profile) as driver:
                print(f"✅ Profile '{profile_name}' - Driver created successfully")
                
                # Test basic navigation
                driver.get("https://web.whatsapp.com")
                print(f"✅ Profile '{profile_name}' - Successfully navigated to WhatsApp Web")
                
                # Wait a moment
                import time
                time.sleep(2)
                
                print(f"✅ Profile '{profile_name}' - Test completed successfully")
                
        except Exception as e:
            print(f"❌ Profile '{profile_name}' - Error: {e}")
            return False
    
    print("\n🎉 All profile tests completed!")
    return True

if __name__ == "__main__":
    success = test_driver_setup()
    if success:
        print("\n✅ ChromeDriver setup is working correctly!")
        print("You can now run your WhatsApp automation script.")
    else:
        print("\n❌ There are still issues with the ChromeDriver setup.")
        print("Please check the error messages above and try running fix_chromedriver.py again.")
