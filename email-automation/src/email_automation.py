#!/usr/bin/env python3
"""
EmailAutomation Class - Main automation functionality
"""

import warnings
from typing import List, Tuple

# Suppress urllib3 OpenSSL warning on macOS
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

# Import our custom modules
from src.core.config import Config
from src.utils.email_utils import EmailUtils
from src.services.sheets_manager import SheetsManager
from src.services.email_draft_manager import EmailDraftManager
from src.services.email_generator import EmailGenerator
from src.ui.user_interface import UserInterface


class EmailAutomation:
    """Main email automation orchestrator"""
    
    def __init__(self):
        self.sheets_manager = SheetsManager()
        self.email_generator = EmailGenerator()
        self.ui = UserInterface()
        
    def save_emails_to_drafts(self) -> None:
        """Save emails to drafts folder from Google Sheets"""
        if not self.sheets_manager.is_connected():
            print("❌ Google Sheets not connected")
            return
        
        # Get email configuration
        email_config = Config.get_email_config()
        email_draft_manager = EmailDraftManager(email_config)
        
        if not email_draft_manager.validate_config():
            return
        
        email_draft_manager.print_config_info()
        
        # Get Google Sheets URLs from environment
        env_urls = Config.get_sheets_urls()
        
        if env_urls:
            print(f"📊 Using {len(env_urls)} sheet(s) from .env file")
            self._process_multiple_sheets_for_drafts(env_urls, email_draft_manager)
            return
        
        # Manual input if no .env URLs
        print("❌ No Google Sheets URLs found in .env file!")
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
        
        print(f"\n🔄 Starting email draft saving process...")
        print(f"📊 Sheet ID: {sheet_id}")
        if sheet_name:
            print(f"📋 Target sheet: {sheet_name}")
        else:
            print("📋 Processing all sheets")
        
        # Process the sheet
        self._process_single_sheet_for_drafts(sheet_id, sheet_name, email_draft_manager)
    
    def _process_multiple_sheets_for_drafts(self, urls: List[str], email_draft_manager: EmailDraftManager) -> None:
        """Process multiple sheets for saving email drafts"""
        # Initialize counters
        total_emails_sent = 0
        total_total_rows = 0
        total_approved_rows = 0
        total_not_approved_rows = 0
        
        for i, url in enumerate(urls, 1):
            sheet_id = EmailUtils.extract_sheet_id_from_url(url)
            self.ui.display_processing_sheet_info(i, len(urls), sheet_id)
            
            # Optional: Get specific sheet name
            sheet_name = self.ui.get_user_input(
                f"📝 Enter specific sheet name for sheet {i} (or press Enter for all sheets): "
            )
            sheet_name = sheet_name if sheet_name else None
            
            print(f"🔄 Starting email draft saving process for sheet {i}...")
            success, emails_sent, total_rows, approved_rows, not_approved_rows = self._process_single_sheet_for_drafts(
                sheet_id, sheet_name, email_draft_manager
            )
            
            total_emails_sent += emails_sent
            total_total_rows += total_rows
            total_approved_rows += approved_rows
            total_not_approved_rows += not_approved_rows
            
            if not success:
                print(f"❌ Processing failed for sheet {i}")
                break
        
        # Display final summary
        self.ui.display_summary(total_total_rows, total_approved_rows, total_not_approved_rows, total_emails_sent)
    
    def _process_single_sheet_for_drafts(self, sheet_id: str, sheet_name: str = None, email_draft_manager: EmailDraftManager = None) -> tuple:
        """Process a single Google Sheet for saving email drafts"""
        try:
            # Open the spreadsheet
            spreadsheet = self.sheets_manager.get_spreadsheet_by_id(sheet_id)
            print(f"📊 Processing: {spreadsheet.title}")
            
            # Get worksheets to process
            worksheets = (
                [spreadsheet.worksheet(sheet_name)]
                if sheet_name
                else spreadsheet.worksheets()
            )
            
            # Initialize counters
            emails_sent = 0
            total_rows = 0
            approved_rows = 0
            not_approved_rows = 0
            
            # Process each worksheet
            for worksheet in worksheets:
                print(f"   📋 Checking worksheet: {worksheet.title}")
                
                # Check permissions before processing
                if not self.sheets_manager.check_sheet_permissions(worksheet):
                    print(f"❌ SKIPPING worksheet '{worksheet.title}' due to permission issues")
                    print("   Please contact the spreadsheet owner to:")
                    print("   1. Remove sheet protection from the 'sent' column")
                    print("   2. Grant edit permissions to your service account")
                    continue
                
                processed, sent, approved, not_approved = self._process_worksheet_for_drafts(
                    worksheet, email_draft_manager
                )
                
                total_rows += processed
                emails_sent += sent
                approved_rows += approved
                not_approved_rows += not_approved
            
            # Display summary for this sheet
            self.ui.display_summary(total_rows, approved_rows, not_approved_rows, emails_sent)
            return True, emails_sent, total_rows, approved_rows, not_approved_rows
            
        except Exception as e:
            print(f"❌ Error processing spreadsheet: {e}")
            print(f"Make sure the Google Sheets ID is correct and you have proper access permissions")
            return False, 0, 0, 0, 0
    
    def _process_worksheet_for_drafts(self, worksheet, email_draft_manager: EmailDraftManager) -> Tuple[int, int, int, int]:
        """Process a single worksheet for saving email drafts"""
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
            
            # Check if should save email draft
            should_save, missing_reasons = EmailUtils.should_save_email_draft(record)
            
            if should_save:
                print(f"📧 Creating draft for: {email}")
                
                # Save email to drafts
                success = email_draft_manager.save_email_to_drafts(email, subject, body, name)
                
                if success:
                    emails_sent += 1
                    # Mark as processed in the worksheet
                    mark_success = self.sheets_manager.mark_as_sent(worksheet, i, headers)
                    
                    if not mark_success:
                        print("❌ STOPPING EXECUTION: Cannot mark emails as processed due to permission issues")
                        print("   This prevents proper tracking and could lead to duplicate processing")
                        print("   Please fix sheet permissions before continuing")
                        return total_rows, emails_sent, approved_rows, not_approved_rows
                    
                    # Add rate limiting
                    email_draft_manager.add_rate_limiting()
                    
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

        # Show generation options
        while True:
            self.ui.show_generation_options()
            choice = self.ui.get_generation_choice()
            
            if choice == "1":
                print("\n📄 Generating for entire sheet...")
                self._handle_full_sheet_generation()
                break
            elif choice == "2":
                print("\n📝 Generating for specific row...")
                self._handle_row_specific_generation()
                break
            elif choice == "3":
                print("\n🔙 Returning to main menu...")
                return
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

    def _handle_full_sheet_generation(self) -> None:
        """Handle full sheet generation workflow"""
        # Get Google Sheets URLs from environment
        env_urls = Config.get_sheets_urls()

        if env_urls:
            print(f"📊 Using {len(env_urls)} sheet(s) from .env file")
            self._process_multiple_sheets_for_generation(env_urls)
            return

        # Manual input if no .env URLs
        print("❌ No Google Sheets URLs found in .env file!")
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

    def _handle_row_specific_generation(self) -> None:
        """Handle row-specific generation workflow"""
        # Get Google Sheets URLs from environment
        env_urls = Config.get_sheets_urls()
        
        if not env_urls:
            print("❌ No Google Sheets URLs found in .env file!")
            print("   Please add GOOGLE_SHEETS_URLS to your .env file")
            return
        
        # Use the first URL or let user choose if multiple
        if len(env_urls) == 1:
            sheet_url = env_urls[0]
            sheet_id = EmailUtils.extract_sheet_id_from_url(sheet_url)
            print(f"📊 Using sheet from .env: {sheet_id}")
        else:
            print("📊 Multiple sheets found in .env file:")
            for i, url in enumerate(env_urls, 1):
                sheet_id_display = EmailUtils.extract_sheet_id_from_url(url)
                print(f"   {i}. {sheet_id_display}")
            
            choice = self.ui.get_user_input("👉 Select sheet number: ")
            try:
                sheet_index = int(choice) - 1
                if 0 <= sheet_index < len(env_urls):
                    sheet_url = env_urls[sheet_index]
                    sheet_id = EmailUtils.extract_sheet_id_from_url(sheet_url)
                else:
                    print("❌ Invalid sheet selection!")
                    return
            except ValueError:
                print("❌ Please enter a valid number!")
                return
        
        # Get specific sheet name
        sheet_name = self.ui.get_user_input(
            "📝 Enter specific sheet name (required for row selection): "
        )
        if not sheet_name:
            print("❌ Sheet name is required for row-specific generation")
            return

        success = self._process_single_row_generation(sheet_id, sheet_name)
        if success:
            print("\n✅ Row-specific email generation completed!")
        else:
            print("\n❌ Row-specific email generation failed!")
    
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
        
        print(f"📊 Found {len(records)} rows in worksheet '{worksheet.title}'")
        
        # Process each row
        processed_count = 0
        approved_count = 0
        already_sent_count = 0
        not_approved_count = 0
        
        for idx, row in enumerate(records, start=2):  # Start from row 2 (header is row 1)
            name = row.get("Name", "Unknown")
            
            # Check if email has already been sent
            is_sent = str(row.get("SENT?", "")).strip().lower()
            if is_sent in Config.SENT_VALUES:
                already_sent_count += 1
                print(f"⏭️  Skipping row {idx}: {name} - Email already sent")
                continue
                
            # Check if "Read For Body?" column is "Approved"
            read_for_body = row.get("Read For Body?", "").strip().lower()
            
            if read_for_body == Config.APPROVED_STATUS:
                approved_count += 1
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
            else:
                not_approved_count += 1
                if idx <= 5:  # Show details for first 5 rows only
                    print(f"⏭️  Skipping row {idx}: {name} - Status: '{read_for_body}' (not approved)")
        
        # Show summary
        print(f"\n📊 Processing Summary for '{worksheet.title}':")
        print(f"   Total rows: {len(records)}")
        print(f"   Already sent: {already_sent_count}")
        print(f"   Approved for generation: {approved_count}")
        print(f"   Not approved: {not_approved_count}")
        print(f"   Successfully processed: {processed_count}")
        
        if approved_count == 0:
            print(f"💡 No rows found with 'Read For Body?' = 'Approved'")
            print(f"   Please set the 'Read For Body?' column to 'Approved' for the rows you want to generate emails for")
        
        self.ui.display_worksheet_completion(worksheet.title, processed_count)
        return True
    
    def _process_single_row_generation(self, sheet_id: str, sheet_name: str) -> bool:
        """Process a single row for email generation"""
        if not self.sheets_manager.is_connected():
            print("❌ Google Sheets not connected")
            return False

        try:
            # Open the spreadsheet
            spreadsheet = self.sheets_manager.get_spreadsheet_by_id(sheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
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
                return False
            
            # Get row number from user
            print(f"\n📋 Worksheet '{worksheet.title}' has {len(records)} rows (rows 2-{len(records) + 1})")
            
            # Get row number from user
            row_num = self.ui.get_row_number(len(records))
            if row_num == 0:
                print("❌ No row selected")
                return False
            
            # Get the specific row data (convert from 1-based to 0-based indexing)
            row_index = row_num - 2  # Subtract 2 because records start from row 2
            if row_index < 0 or row_index >= len(records):
                print("❌ Invalid row number")
                return False
            
            row_data = records[row_index]
            
            # Display row information
            self.ui.display_row_info(row_num, row_data)
            
            # Confirm generation
            name = row_data.get("Name", "Unknown")
            if not self.ui.confirm_row_generation(row_num, name):
                print("❌ Generation cancelled by user")
                return False
            
            # Check if email has already been sent
            is_sent = str(row_data.get("SENT?", "")).strip().lower()
            if is_sent in Config.SENT_VALUES:
                print(f"⚠️  Warning: Email for {name} has already been sent")
                if not self.ui.get_yes_no_input("Continue anyway? (y/n): "):
                    return False
            
            # Check if "Read For Body?" column is "Approved"
            read_for_body = row_data.get("Read For Body?", "").strip().lower()
            
            if read_for_body != Config.APPROVED_STATUS:
                print(f"⚠️  Warning: 'Read For Body?' status is '{read_for_body}', not 'Approved'")
                if not self.ui.get_yes_no_input("Continue anyway? (y/n): "):
                    return False
            
            print(f"📧 Processing row {row_num}: {name}")
            
            # Generate email content
            email_content = self.email_generator.generate_email_content(row_data)
            
            if email_content.startswith("Error:"):
                print(f"❌ {email_content}")
                return False
            
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
                worksheet, row_num, column_map, subject, body
            )
            
            if success:
                print(f"✅ Successfully generated email for row {row_num}: {name}")
                return True
            else:
                print(f"❌ Failed to update worksheet for row {row_num}: {name}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing row: {e}")
            return False
    
    def run(self) -> None:
        """Main function to run the email automation suite"""
        self.ui.display_welcome_message()
        
        while True:
            self.ui.show_menu()
            choice = self.ui.get_menu_choice()
            
            if choice == "1":
                print("\n� Starting Email Draft Saving Process...")
                self.save_emails_to_drafts()
                
            elif choice == "2":
                print("\n✍️  Starting Email Body Generation Process...")
                self.generate_email_bodies()
                
            elif choice == "3":
                self.ui.display_goodbye_message()
                break
                
            else:
                self.ui.display_invalid_choice_message()
            
            self.ui.wait_for_continue()
