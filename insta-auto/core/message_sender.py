import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from config.settings import logger, PAGE_LOAD_WAIT, MESSAGE_CHAR_DELAY, COOLDOWN_DELAY

class InstagramMessageSender:
    def __init__(self, driver, message_text):
        self.driver = driver
        self.message_text = message_text

    def send_message(self, username):
        """Send message to a single user"""
        try:
            self.driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(PAGE_LOAD_WAIT)

            if self._is_profile_invalid():
                logger.warning(f"❌ Skipped {username}: Profile not found or banned.")
                return False

            if not self._open_message_window():
                return False

            if not self._send_message_text():
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Failed processing {username}: {str(e)}")
            return False

    def _is_profile_invalid(self):
        return any(x in self.driver.page_source for x in 
                  ["Page Not Found", "Sorry, this page isn't available."])

    def _open_message_window(self):
        try:
            message_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[text()='Message' and @role='button']"))
            )
            self.driver.execute_script("arguments[0].click();", message_button)
            logger.info("✅ Message window opened")
            time.sleep(2)
            return True
        except TimeoutException:
            logger.error("❌ Message button not found")
            return False

    def _send_message_text(self):
        try:
            text_area = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )
            text_area.clear()
            
            for char in self.message_text:
                text_area.send_keys(char)
                time.sleep(MESSAGE_CHAR_DELAY)
            
            send_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and text()='Send']"))
            )
            self.driver.execute_script("arguments[0].click();", send_btn)
            time.sleep(COOLDOWN_DELAY)
            
            return self.message_text in self.driver.page_source
        except Exception as e:
            logger.error(f"❌ Error sending message: {str(e)}")
            return False
