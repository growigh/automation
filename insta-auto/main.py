import os
import time
from tqdm import tqdm
from utils.driver_setup import setup_chrome_driver
from utils.data_handler import (
    load_usernames, 
    record_messaged_user, 
    remove_username_from_file
)
from core.message_sender import InstagramMessageSender
from config.settings import DEFAULT_MESSAGE, logger

def main():
    driver = None
    try:
        usernames = load_usernames()
        if not usernames:
            logger.info("No new usernames to process")
            return

        driver = setup_chrome_driver()
        driver.get("https://www.instagram.com/")
        
        input("\nLog in manually if not already, then press Enter to continue...")
        
        if "Login" in driver.title or "Sign In" in driver.page_source:
            raise Exception("Not logged in to Instagram")

        sender = InstagramMessageSender(driver, DEFAULT_MESSAGE)
        
        for username in tqdm(usernames, desc="Sending Messages"):
            if sender.send_message(username):
                record_messaged_user(username, time.strftime('%Y-%m-%d %H:%M:%S'))
                remove_username_from_file(username)
                logger.info(f"✅ Successfully messaged {username}")

    except Exception as e:
        logger.error(f"❌ Critical error: {str(e)}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":    
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
