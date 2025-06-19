import time
import getpass
import os
import stat
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from contextlib import contextmanager
import chromedriver_autoinstaller
import shutil

# Get current username dynamically
USERNAME = getpass.getuser()
CHROME_BASE_PATH = f"/Users/{USERNAME}/Library/Application Support/Google/Chrome"

# === CONFIGURATION ===
# Define multiple Chrome profiles
CHROME_PROFILES = [
    {
        "user_data_dir": f"{CHROME_BASE_PATH}/Profile 1",
        "profile_dir": "one"
    },
    {
        "user_data_dir": f"{CHROME_BASE_PATH}/Profile 3", 
        "profile_dir": "three"
    },
    {
        "user_data_dir": f"{CHROME_BASE_PATH}/Profile 4", 
        "profile_dir": "four"
    },
]

def get_chromedriver_path():
    """Get ChromeDriver path with multiple fallback strategies"""
    try:
        # Strategy 1: Try chromedriver-autoinstaller (most reliable for macOS)
        print("🔄 Trying chromedriver-autoinstaller...")
        chromedriver_path = chromedriver_autoinstaller.install()
        
        # Make sure the driver is executable
        if chromedriver_path and os.path.exists(chromedriver_path):
            # Set executable permissions
            os.chmod(chromedriver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            print(f"✅ ChromeDriver found: {chromedriver_path}")
            return chromedriver_path
            
    except Exception as e:
        print(f"⚠️ chromedriver-autoinstaller failed: {e}")
    
    try:
        # Strategy 2: Try webdriver-manager with custom cache and permissions fix
        print("🔄 Trying webdriver-manager...")
        driver_path = ChromeDriverManager().install()
        
        if driver_path and os.path.exists(driver_path):
            # Fix permissions for macOS
            os.chmod(driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            print(f"✅ ChromeDriver found: {driver_path}")
            return driver_path
            
    except Exception as e:
        print(f"⚠️ webdriver-manager failed: {e}")
    
    # Strategy 3: Try system ChromeDriver
    try:
        print("🔄 Trying system ChromeDriver...")
        system_paths = [
            "/usr/local/bin/chromedriver",
            "/opt/homebrew/bin/chromedriver",
            "/usr/bin/chromedriver"
        ]
        
        for path in system_paths:
            if os.path.exists(path):
                os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✅ System ChromeDriver found: {path}")
                return path
                
    except Exception as e:
        print(f"⚠️ System ChromeDriver check failed: {e}")
    
    raise Exception("❌ Could not find or install ChromeDriver. Please install Chrome and ChromeDriver manually.")

def setup_driver(profile):
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={profile['user_data_dir']}")
    chrome_options.add_argument(f"--profile-directory={profile['profile_dir']}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    
    # Performance optimizations
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--disable-preconnect")
    chrome_options.add_argument("--disable-prefetch")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-component-extensions-with-background-pages")
    
    # macOS specific fixes
    if platform.system() == "Darwin":  # macOS
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-popup-blocking")

    try:
        # Get ChromeDriver path with fallback strategies
        chromedriver_path = get_chromedriver_path()
        service = Service(chromedriver_path)
        
        print(f"🚀 Starting Chrome with profile: {profile['profile_dir']}")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Hide webdriver property for better compatibility
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        print(f"❌ Failed to setup driver for profile {profile['profile_dir']}: {e}")
        raise

@contextmanager
def managed_driver(profile):
    driver = None
    try:
        driver = setup_driver(profile)
        yield driver
    finally:
        if driver:
            driver.quit()

def cleanup_driver(driver):
    try:
        if driver:
            driver.quit()
    except:
        pass 

def safe_get(driver, url, profile, retries=3, delay=2):
    for attempt in range(retries):
        try:
            driver.get(url)
            return True
        except Exception as e:
            print(f"⚠️ Retry {attempt+1} for {url} due to error: {e}")
            if "invalid session id" in str(e).lower():
                try:
                    print("⚠️ Session invalid, cleaning up old session...")
                    cleanup_driver(driver)  # Clean up the invalid session
                    print("⚠️ Creating new managed driver...")
                    with managed_driver(profile) as new_driver:
                        driver = new_driver
                        driver.get(url)
                        return True
                except Exception as setup_err:
                    print(f"Failed with managed driver: {setup_err}")
            
            time.sleep(delay) 
    return False

def wait_for_send_button(driver, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Send"]'))
    )

def clear_webdriver_cache():
    """Clear webdriver-manager cache which might be corrupted"""
    cache_paths = [
        f"/Users/{USERNAME}/.wdm",
        f"/Users/{USERNAME}/.cache/selenium"
    ]
    
    for cache_path in cache_paths:
        if os.path.exists(cache_path):
            try:
                print(f"🧹 Clearing cache: {cache_path}")
                shutil.rmtree(cache_path)
                print(f"✅ Cache cleared: {cache_path}")
            except Exception as e:
                print(f"⚠️ Failed to clear cache {cache_path}: {e}")

