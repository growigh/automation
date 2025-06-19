from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from config.settings import CHROME_OPTIONS, logger

def setup_chrome_driver():
    chrome_options = Options()
    
    # Add chrome arguments
    chrome_options.add_argument(f"--user-data-dir={CHROME_OPTIONS['user_data_dir']}")
    chrome_options.add_argument(f"--profile-directory={CHROME_OPTIONS['profile_directory']}")
    
    for arg in CHROME_OPTIONS['arguments']:
        chrome_options.add_argument(arg)
    
    # Add experimental options
    for key, value in CHROME_OPTIONS['experimental_options'].items():
        chrome_options.add_experimental_option(key, value)
    
    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {str(e)}")
        raise