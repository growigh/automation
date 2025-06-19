import time
import threading
from urllib.parse import quote
from typing import List, Dict, Set
from selenium.webdriver.remote.webdriver import WebDriver
from tqdm import tqdm

from config.driver_setup import (
    safe_get, 
    wait_for_send_button, 
    managed_driver,
    CHROME_PROFILES
)
from utils.get_delay import get_delay
from utils.normalize_number import normalize_number
from utils.contact_manager import (
    load_all_contacts, 
    load_contacted_numbers, 
    safely_append_to_contacted,
    remove_contacted_from_source_files
)
from config.config import CSV_FOLDER, MESSAGE, COLUMN_NAME

class WhatsAppMessageSender:
    def __init__(self):
        self.contacted_lock = threading.Lock()
        self.contacted_numbers: Set[str] = set()
        self.load_contacted_numbers()

    def load_contacted_numbers(self) -> None:
        """Thread-safe loading of previously contacted numbers"""
        with self.contacted_lock:
            self.contacted_numbers = {
                normalize_number(num) for num in load_contacted_numbers()
            }

    def process_single_contact(
        self, 
        driver: WebDriver, 
        contact: Dict, 
        profile_name: str,
        encoded_message: str
    ) -> bool:
        """Process a single contact and return success status"""
        try:
            number = contact[COLUMN_NAME]
            normalized_number = normalize_number(number)
            
            if not number or not normalized_number:
                print(f"[Profile: {profile_name}] ⚠️ Invalid phone number format: {number}")
                return False

            # Check if already contacted
            with self.contacted_lock:
                if normalized_number in self.contacted_numbers:
                    print(f"[Profile: {profile_name}] ⏩ Skipping {number} - already contacted")
                    return False

            url = f"https://web.whatsapp.com/send?phone={number}&text={encoded_message}"
            
            # Retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if not safe_get(driver, url, {"profile_dir": profile_name}):
                        raise Exception("Failed to open chat")
                        
                    send_btn = wait_for_send_button(driver)
                    send_btn.click()
                    time.sleep(1)  # Wait for message to send
                    
                    with self.contacted_lock:
                        safely_append_to_contacted(number)
                        self.contacted_numbers.add(normalized_number)
                        
                    print(f"[Profile: {profile_name}] ✅ Message sent to {number}")
                    time.sleep(get_delay())
                    return True
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"[Profile: {profile_name}] ❌ Failed to send to {number} after {max_retries} attempts: {e}")
                        return False
                    print(f"[Profile: {profile_name}] Retrying {number} ({attempt + 2}/{max_retries})...")
                    time.sleep(1)
                    
        except KeyError:
            print(f"[Profile: {profile_name}] ⚠️ Missing phone number column in contact: {contact}")
            return False

        return False

    def process_contacts(self, profile: Dict, contact_subset: List[Dict]) -> None:
        """Process a subset of contacts for a given Chrome profile"""
        encoded_message = quote(MESSAGE)
        profile_name = profile['profile_dir']
        
        stats = {
            'successful_sends': 0,
            'failed_sends': 0,
            'skipped': 0
        }
        
        # Track successfully sent numbers for removal from source files
        successfully_sent_numbers = []

        try:
            with managed_driver(profile) as driver:
                print(f"[Profile: {profile_name}] Starting WhatsApp automation...")
                safe_get(driver, "https://web.whatsapp.com", profile)
                
                # QR code scan handling
                if not self._handle_qr_code_scan(profile_name):
                    return
                
                print(f"[Profile: {profile_name}] Processing {len(contact_subset)} contacts")
                
                for contact in tqdm(contact_subset, desc=f"[Profile: {profile_name}] Sending messages"):
                    result = self.process_single_contact(driver, contact, profile_name, encoded_message)
                    
                    if result:
                        stats['successful_sends'] += 1
                        # Add to successfully sent numbers for removal
                        successfully_sent_numbers.append(contact[COLUMN_NAME])
                    else:
                        if contact[COLUMN_NAME] in self.contacted_numbers:
                            stats['skipped'] += 1
                        else:
                            stats['failed_sends'] += 1

        except Exception as e:
            print(f"[Profile: {profile_name}] Fatal error: {str(e)}")
        finally:
            self._print_summary(profile_name, stats)
            
            # Remove successfully sent contacts from source files
            if successfully_sent_numbers:
                print(f"[Profile: {profile_name}] Removing {len(successfully_sent_numbers)} sent contacts from source files...")
                remove_contacted_from_source_files(CSV_FOLDER, successfully_sent_numbers)

    def _handle_qr_code_scan(self, profile_name: str) -> bool:
        """Handle QR code scanning with timeout"""
        print(f"[Profile: {profile_name}] Please scan the QR code within 60 seconds...")
        start_time = time.time()
        
        while True:
            user_input = input(f"[Profile: {profile_name}] Press Enter after scanning QR code (or 'q' to quit)...\n")
            if user_input.lower() == 'q':
                print(f"[Profile: {profile_name}] Exiting program...\n")
                return False
            if time.time() - start_time > 60:
                raise TimeoutError(f"[Profile: {profile_name}] QR code scan timeout\n")
            return True

    def _print_summary(self, profile_name: str, stats: Dict) -> None:
        """Print summary of message sending results"""
        print(f"\n\n[Profile: {profile_name}] Summary:")
        print(f"[Profile: {profile_name}] Successfully sent: {stats['successful_sends']}")
        print(f"[Profile: {profile_name}] Failed to send: {stats['failed_sends']}")
        print(f"[Profile: {profile_name}] Total processed: {stats['successful_sends'] + stats['failed_sends']}")
        print(f"[Profile: {profile_name}] Skipped: {stats['skipped']}")

    def run(self) -> None:
        """Main method to start the WhatsApp automation"""
        try:
            all_contacts = load_all_contacts(CSV_FOLDER)
            total_contacts = len(all_contacts)
            
            if total_contacts == 0:
                print("No contacts found in CSV folder")
                return
                
            profile_count = len(CHROME_PROFILES)
            if profile_count == 0:
                print("No Chrome profiles configured")
                return
                
            print(f"Processing {total_contacts} contacts using {profile_count} Chrome profiles")
            
            # Distribute contacts among profiles
            contacts_per_profile = total_contacts // profile_count
            remainder = total_contacts % profile_count
            
            threads = []
            start_index = 0
            
            # Create and start threads for each profile
            for i, profile in enumerate(CHROME_PROFILES):
                count = contacts_per_profile + (1 if i < remainder else 0)
                end_index = start_index + count
                profile_contacts = all_contacts[start_index:end_index]
                start_index = end_index
                
                thread = threading.Thread(
                    target=self.process_contacts,
                    args=(profile, profile_contacts)
                )
                threads.append(thread)
                thread.start()
                
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
                
            print("\nAll WhatsApp automation threads completed.")

        except Exception as e:
            print(f"Error in main thread: {str(e)}")