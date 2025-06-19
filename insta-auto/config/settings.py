import logging

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chrome configuration
CHROME_OPTIONS = {
    "user_data_dir": "/Users/ayushkumar/Library/Application Support/Google/Chrome/Profile 1",
    "profile_directory": "Growigh",
    "arguments": [
        "--start-maximized",
        "--disable-notifications"
    ],
    "experimental_options": {
        "excludeSwitches": ["enable-automation"],
        "useAutomationExtension": False
    }
}

# File paths
USERNAMES_FILE = "usernames.csv"
MESSAGED_FILE = "messaged.csv"

# Message content
DEFAULT_MESSAGE = "test test"

# Timing configurations
PAGE_LOAD_WAIT = 5
MESSAGE_CHAR_DELAY = 0.1
COOLDOWN_DELAY = 2