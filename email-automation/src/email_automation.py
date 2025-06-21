#!/usr/bin/env python3
"""
EmailAutomation Class - Main automation functionality
"""

import os
import warnings
import time
import logging
from typing import List, Dict, Tuple

# Suppress urllib3 OpenSSL warning on macOS
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

# Import our custom modules
from src.core.config import Config
from src.utils.email_utils import EmailUtils
from src.services.sheets_manager import SheetsManager
from src.services.email_sender import EmailSender
from src.services.email_generator import EmailGenerator
from src.ui.user_interface import UserInterface

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


class EmailAutomation:
    """Main email automation orchestrator"""
    
    def __init__(self):
        self.sheets_manager = SheetsManager()
        self.email_generator = EmailGenerator()
        self.ui = UserInterface()
        
    def send_emails(self) -> None:
        """Send emails from Google Sheets"""
        if not self.sheets_manager.is_connected():
            print("❌ Google Sheets not connected")
            return
        
        # Get email configuration
        email_config = Config.get_email_config()
        email_sender = EmailSender(email_config)
        
        if not email_sender.validate_config():
            return
        
        email_sender.print_config_info()
        
        # Get sheets URLs from config
        sheets_urls = Config.get_sheets_urls()
        
        # Initialize counters
        emails_sent = 0
        total_rows = 0
        approved_rows = 0
        not_approved_rows = 0
        
        # Process each sheet
        for sheet_url in sheets_urls:
            if not sheet_url.strip():
                continue
            
            try:
                spreadsheet = self.sheets_manager.get_spreadsheet_by_url(sheet_url)
                print(f"📊 Processing: {spreadsheet.title}")
                
                # Process each worksheet
                for worksheet in spreadsheet.worksheets():
                    processed, sent, approved, not_approved = self._process_worksheet_for_sending(
                        worksheet, email_sender
                    )
                    
                    total_rows += processed
                    emails_sent += sent
                    approved_rows += approved
                    not_approved_rows += not_approved
                    
            except Exception as e:
                print(f"❌ Error processing sheet {sheet_url}: {e}")
        
        # Display summary
        self.ui.display_summary(total_rows, approved_rows, not_approved_rows, emails_sent)
    
    def _process_worksheet_for_sending(self, worksheet, email_sender: EmailSender) -> Tuple[int, int, int, int]:
        """Process a single worksheet for sending emails"""
        records = self.sheets_manager.get_worksheet_records(worksheet)
        headers = worksheet.row_values(1)
        
        total_rows = 0
        emails_sent = 0
        approved_rows = 0
        not_approved_rows = 0
        
        for i, record in enumerate(records, 1):
            total_rows += 1
            
            # Extract and validate record data
            status = str(record.get("Status", "")).strip().lower()
            email = str(record.get("Email", "")).strip()
            subject = str(record.get("Subject", "")).strip()
            body = str(record.get("Body", "")).strip()
            name = str(record.get("Name", "")).strip()
            
            # Track status counts
            if status == Config.APPROVED_STATUS:
                approved_rows += 1
            else:
                not_approved_rows += 1
            
            # Check if should send email
            should_send, missing_reasons = EmailUtils.should_send_email(record)
            
            if should_send:
                print(f"📧 Sending email to: {email}")
                
                # Send the email
                success = email_sender.send_email(email, subject, body, name)
                
                if success:
                    emails_sent += 1
                    # Mark as sent in the worksheet
                    self.sheets_manager.mark_as_sent(worksheet, i, headers)
                    # Add rate limiting
                    email_sender.add_rate_limiting()
                    
            elif status == Config.APPROVED_STATUS and missing_reasons:
                print(f"⏭️  Skipping row {i}: {', '.join(missing_reasons)}")
        
        return total_rows, emails_sent, approved_rows, not_approved_rows
    
    def generate_email_bodies(self) -> None:
        """Generate email bodies using AI"""
        if not self.email_generator.is_ai_available():
            print("❌ AI dependencies not installed. Please install:")
            print("   pip install langchain-core langchain-google-genai")
            return
        
        if not self.email_generator.initialize_llm():
            return
        
        if not self.email_generator.load_email_prompt():
            return
        
        # Get Google Sheets URLs from environment
        env_urls = Config.get_sheets_urls()
        
        if env_urls:
            self.ui.display_sheets_info(env_urls)
            use_env = self.ui.get_yes_no_input("\n🤔 Use URLs from .env file? (y/n): ")
            
            if use_env:
                self._process_multiple_sheets_for_generation(env_urls)
                return
        
        # Manual input if no .env URLs or user chooses manual input
        print("📋 Manual Google Sheets ID Entry")
        sheet_input = self.ui.get_user_input("📋 Enter Google Sheets ID or URL: ")
        
        if not sheet_input:
            print("❌ Please provide a valid Google Sheets ID or URL")
            return
        
        # Extract sheet ID if URL is provided
        sheet_id = EmailUtils.extract_sheet_id_from_url(sheet_input)
        
        # Optional: Get specific sheet name
        sheet_name = self.ui.get_user_input(
            "📝 Enter specific sheet name (or press Enter for all sheets): "
        )
        sheet_name = sheet_name if sheet_name else None
        
        self.ui.display_processing_info(sheet_id, sheet_name)
        
        # Process the sheet
        success = self._process_single_sheet_for_generation(sheet_id, sheet_name)
        self.ui.display_completion_message(success)
    
    def _process_multiple_sheets_for_generation(self, urls: List[str]) -> None:
        """Process multiple sheets for email generation"""
        all_successful = True
        
        for i, url in enumerate(urls, 1):
            sheet_id = EmailUtils.extract_sheet_id_from_url(url)
            self.ui.display_processing_sheet_info(i, len(urls), sheet_id)
            
            # Optional: Get specific sheet name
            sheet_name = self.ui.get_user_input(
                f"📝 Enter specific sheet name for sheet {i} (or press Enter for all sheets): "
            )
            sheet_name = sheet_name if sheet_name else None
            
            print(f"🔄 Starting email generation process for sheet {i}...")
            success = self._process_single_sheet_for_generation(sheet_id, sheet_name)
            
            if not success:
                all_successful = False
                print(f"❌ Processing failed for sheet {i}")
        
        if all_successful:
            print(f"\n🎉 All sheets processed successfully!")
        else:
            print(f"\n❌ Some sheets failed to process. Please check the errors above.")
    
    def _process_single_sheet_for_generation(self, sheet_id: str, sheet_name: str = None) -> bool:
        """Process a single Google Sheet for email generation"""
        if not self.sheets_manager.is_connected():
            print("❌ Google Sheets not connected")
            return False
        
        try:
            # Open the spreadsheet
            spreadsheet = self.sheets_manager.get_spreadsheet_by_id(sheet_id)
            
            # Get worksheets to process
            worksheets = (
                [spreadsheet.worksheet(sheet_name)]
                if sheet_name
                else spreadsheet.worksheets()
            )
            
            for worksheet in worksheets:
                success = self._process_worksheet_for_generation(worksheet)
                if not success:
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error processing spreadsheet: {e}")
            print(f"Make sure the Google Sheets ID is correct and you have proper access permissions")
            return False
    
    def _process_worksheet_for_generation(self, worksheet) -> bool:
        """Process a single worksheet for email generation"""
        print(f"\nProcessing worksheet: {worksheet.title}")
        
        # Get column mapping and validate required columns
        column_map = self.sheets_manager.get_column_mapping(worksheet)
        is_valid, missing_columns = self.sheets_manager.validate_required_columns(
            column_map, Config.REQUIRED_GENERATION_COLUMNS
        )
        
        if not is_valid:
            print(f"❌ ERROR: Missing required columns in worksheet '{worksheet.title}': {', '.join(missing_columns)}")
            print(f"   Available columns: {list(column_map.keys())}")
            print(f"   Required columns: {Config.REQUIRED_GENERATION_COLUMNS}")
            print("   Please add the missing columns to your spreadsheet and try again.")
            return False
        
        # Get all records
        records = self.sheets_manager.get_worksheet_records(worksheet)
        
        if not records:
            print(f"No data found in worksheet {worksheet.title}")
            return True
        
        # Process each row
        processed_count = 0
        for idx, row in enumerate(records, start=2):  # Start from row 2 (header is row 1)
            # Check if "Read For Body?" column is "Approved"
            read_for_body = row.get("Read For Body?", "").strip().lower()
            
            if read_for_body == Config.APPROVED_STATUS:
                name = row.get("Name", "Unknown")
                print(f"📧 Processing row {idx}: {name}")
                
                # Generate email content
                email_content = self.email_generator.generate_email_content(row)
                
                if email_content.startswith("Error:"):
                    print(f"❌ {email_content}")
                    continue
                
                # Debug: Show first 200 characters of generated content
                print(f"  🔍 Generated content preview: {email_content[:200]}...")
                
                # Parse email content to extract subject and body
                subject, body = EmailUtils.parse_email_content(email_content)
                
                # Debug: Show what was extracted
                if subject:
                    print(f"  📝 Extracted subject: {subject}")
                else:
                    print(f"  ⚠️  No subject found in generated content")
                
                # Update the worksheet with generated content
                success = self.email_generator.update_worksheet_with_content(
                    worksheet, idx, column_map, subject, body
                )
                
                if success:
                    processed_count += 1
                
                # Add delay to avoid API rate limits
                self.email_generator.add_api_delay()
        
        self.ui.display_worksheet_completion(worksheet.title, processed_count)
        return True
    
    def run(self) -> None:
        """Main function to run the email automation suite"""
        self.ui.display_welcome_message()
        
        while True:
            self.ui.show_menu()
            choice = self.ui.get_menu_choice()
            
            if choice == "1":
                print("\n📧 Starting Email Sending Process...")
                self.send_emails()
                
            elif choice == "2":
                print("\n✍️  Starting Email Body Generation Process...")
                self.generate_email_bodies()
                
            elif choice == "3":
                self.ui.display_goodbye_message()
                break
                
            else:
                self.ui.display_invalid_choice_message()
            
            self.ui.wait_for_continue()
