#!/usr/bin/env python3
"""
ChromeDriver Diagnostic and Fix Script
Run this script to diagnose and fix ChromeDriver issues on macOS
"""

import os
import sys
import subprocess
import platform
import stat
from pathlib import Path

def run_command(command):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_chrome_version():
    """Check Chrome version"""
    print("🔍 Checking Chrome version...")
    
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            success, stdout, stderr = run_command(f'"{chrome_path}" --version')
            if success:
                print(f"✅ Chrome found: {stdout}")
                return stdout
            else:
                print(f"⚠️ Chrome found but can't get version: {stderr}")
    
    print("❌ Chrome not found. Please install Google Chrome.")
    return None

def fix_chromedriver_permissions():
    """Fix ChromeDriver permissions in common locations"""
    print("🔧 Fixing ChromeDriver permissions...")
    
    # Common ChromeDriver locations
    search_paths = [
        f"/Users/{os.getenv('USER')}/.wdm/drivers/chromedriver",
        f"/Users/{os.getenv('USER')}/.cache/selenium",
        "/usr/local/bin/chromedriver",
        "/opt/homebrew/bin/chromedriver"
    ]
    
    fixed_count = 0
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            try:
                # Find all chromedriver files
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if "chromedriver" in file.lower():
                            file_path = os.path.join(root, file)
                            print(f"🔧 Fixing permissions for: {file_path}")
                            os.chmod(file_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                            fixed_count += 1
            except Exception as e:
                print(f"⚠️ Error fixing permissions in {search_path}: {e}")
    
    if fixed_count > 0:
        print(f"✅ Fixed permissions for {fixed_count} ChromeDriver files")
    else:
        print("ℹ️ No ChromeDriver files found to fix")

def clear_webdriver_cache():
    """Clear webdriver-manager cache"""
    print("🧹 Clearing webdriver-manager cache...")
    
    cache_paths = [
        f"/Users/{os.getenv('USER')}/.wdm",
        f"/Users/{os.getenv('USER')}/.cache/selenium"
    ]
    
    for cache_path in cache_paths:
        if os.path.exists(cache_path):
            try:
                import shutil
                shutil.rmtree(cache_path)
                print(f"✅ Cleared cache: {cache_path}")
            except Exception as e:
                print(f"⚠️ Failed to clear cache {cache_path}: {e}")
        else:
            print(f"ℹ️ Cache not found: {cache_path}")

def install_chromedriver_homebrew():
    """Try to install ChromeDriver via Homebrew"""
    print("🍺 Trying to install ChromeDriver via Homebrew...")
    
    # Check if Homebrew is installed
    success, stdout, stderr = run_command("which brew")
    if not success:
        print("❌ Homebrew not found. Please install Homebrew first:")
        print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    
    # Try to install chromedriver
    success, stdout, stderr = run_command("brew install chromedriver")
    if success:
        print("✅ ChromeDriver installed via Homebrew")
        
        # Fix permissions
        chromedriver_path = "/opt/homebrew/bin/chromedriver"
        if os.path.exists(chromedriver_path):
            os.chmod(chromedriver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            print(f"✅ Fixed permissions for: {chromedriver_path}")
        
        return True
    else:
        print(f"⚠️ Failed to install ChromeDriver via Homebrew: {stderr}")
        return False

def test_chromedriver():
    """Test if ChromeDriver works"""
    print("🧪 Testing ChromeDriver installation...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        import chromedriver_autoinstaller
        
        # Try chromedriver-autoinstaller
        try:
            chromedriver_path = chromedriver_autoinstaller.install()
            os.chmod(chromedriver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://www.google.com")
            driver.quit()
            
            print("✅ ChromeDriver test successful!")
            print(f"✅ Working ChromeDriver path: {chromedriver_path}")
            return True
            
        except Exception as e:
            print(f"❌ ChromeDriver test failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def main():
    print("🚀 ChromeDriver Diagnostic and Fix Script")
    print("=" * 50)
    
    if platform.system() != "Darwin":
        print("❌ This script is designed for macOS only")
        sys.exit(1)
    
    # Step 1: Check Chrome
    chrome_version = check_chrome_version()
    if not chrome_version:
        print("Please install Google Chrome and run this script again.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Step 2: Clear cache
    clear_webdriver_cache()
    
    print("\n" + "=" * 50)
    
    # Step 3: Fix permissions
    fix_chromedriver_permissions()
    
    print("\n" + "=" * 50)
    
    # Step 4: Test ChromeDriver
    if not test_chromedriver():
        print("\n" + "=" * 50)
        print("🔧 Trying to install ChromeDriver via Homebrew...")
        if install_chromedriver_homebrew():
            print("\n" + "=" * 50)
            print("🧪 Testing again after Homebrew installation...")
            test_chromedriver()
    
    print("\n" + "=" * 50)
    print("🎉 Diagnostic complete!")
    print("\nIf you're still having issues, try:")
    print("1. Restart your terminal")
    print("2. Run: pip install --upgrade selenium webdriver-manager chromedriver-autoinstaller")
    print("3. Make sure Google Chrome is up to date")

if __name__ == "__main__":
    main()
