#!/usr/bin/env python3
"""
User interface for email automation
"""

from typing import List, Optional
from src.utils.email_utils import EmailUtils

class UserInterface:
    """Handles user interaction and menu display"""
    
    @staticmethod
    def show_menu():
        """Display the main menu"""
        print("\n" + "="*60)
        print("🚀 Email Automation Suite")
        print("="*60)
        print("1. � Save Emails to Drafts (from Google Sheets)")
        print("2. ✍️  Generate Email Bodies (using AI)")
        print("3. 🚪 Exit")
        print("="*60)
    
    @staticmethod
    def get_menu_choice() -> str:
        """Get user menu choice"""
        return input("👉 Enter your choice (1-3): ").strip()
    
    @staticmethod
    def get_user_input(prompt: str) -> str:
        """Get user input with prompt"""
        return input(prompt).strip()
    
    @staticmethod
    def get_yes_no_input(prompt: str) -> bool:
        """Get yes/no input from user"""
        response = input(prompt).strip().lower()
        return response in ['y', 'yes']
    
    @staticmethod
    def wait_for_continue():
        """Wait for user to press Enter"""
        input("\n📝 Press Enter to continue...")
    
    @staticmethod
    def display_sheets_info(urls: List[str]):
        """Display information about available sheets"""
        print(f"📋 Found {len(urls)} Google Sheets URL(s) in .env file:")
        for i, url in enumerate(urls, 1):
            sheet_id = EmailUtils.extract_sheet_id_from_url(url)
            print(f"   {i}. {url} (ID: {sheet_id})")
    
    @staticmethod
    def display_processing_info(sheet_id: str, sheet_name: Optional[str] = None):
        """Display processing information"""
        print(f"\n🔄 Starting email generation process...")
        print(f"📊 Sheet ID: {sheet_id}")
        if sheet_name:
            print(f"📋 Target sheet: {sheet_name}")
        else:
            print(f"📋 Processing all sheets")
    
    @staticmethod
    def display_completion_message(success: bool):
        """Display completion message"""
        if success:
            print(f"\n✅ Email generation completed!")
            print(f"\n💡 Next steps:")
            print(f"   1. Review generated emails in your Google Sheet")
            print(f"   2. Set 'Status' column to 'Approved' for emails you want to save as drafts")
            print(f"   3. Use option 1 to save the generated emails to drafts")
        else:
            print(f"\n❌ Email generation failed! Please check the errors above.")
    
    @staticmethod
    def display_welcome_message():
        """Display welcome message"""
        print("🎯 Welcome to Email Automation Suite!")
    
    @staticmethod
    def display_goodbye_message():
        """Display goodbye message"""
        print("\n👋 Goodbye! Thanks for using Email Automation Suite!")
    
    @staticmethod
    def display_invalid_choice_message():
        """Display invalid choice message"""
        print("❌ Invalid choice. Please enter 1, 2, or 3.")
    
    @staticmethod
    def display_summary(total_rows: int, approved_rows: int, not_approved_rows: int, emails_sent: int):
        """Display email draft saving summary"""
        print(f"\n📊 Summary:")
        print(f"   Total rows processed: {total_rows}")
        print(f"   Approved rows: {approved_rows}")
        print(f"   Not approved rows: {not_approved_rows}")
        print(f"   Drafts saved: {emails_sent}")
        
        if emails_sent == 0:
            if not_approved_rows > 0 and approved_rows == 0:
                print(f"⚠️  No drafts saved - No approved emails found!")
                print(f"   Change the 'Status' column to 'Approved' for rows you want to save as drafts.")
            elif approved_rows > 0:
                print(f"⚠️  No drafts saved - All approved emails may be missing required fields or already processed.")
            else:
                print(f"⚠️  No drafts saved - No data found in sheets.")
        else:
            print(f"🎉 Successfully saved {emails_sent} drafts!")
    
    @staticmethod
    def display_processing_sheet_info(sheet_num: int, total_sheets: int, sheet_id: str):
        """Display sheet processing information"""
        print(f"\n🔄 Processing sheet {sheet_num}/{total_sheets}: {sheet_id}")
    
    @staticmethod
    def display_worksheet_completion(worksheet_title: str, processed_count: int):
        """Display worksheet completion information"""
        print(f"\n📊 Completed worksheet '{worksheet_title}': {processed_count} emails generated")

    @staticmethod
    def show_generation_options():
        """Display email generation options"""
        print("\n" + "="*50)
        print("✍️ Email Generation Options")
        print("="*50)
        print("1. 📄 Generate for entire sheet")
        print("2. 📝 Generate for specific row")
        print("3. 🔙 Back to main menu")
        print("="*50)
    
    @staticmethod
    def get_generation_choice() -> str:
        """Get user choice for generation type"""
        return input("👉 Enter your choice (1-3): ").strip()
    
    @staticmethod
    def get_row_number(max_rows: int) -> int:
        """Get specific row number from user"""
        while True:
            try:
                row_input = input(f"📝 Enter row number (2-{max_rows + 1}, header is row 1): ").strip()
                if not row_input:
                    return 0
                
                row_num = int(row_input)
                if 2 <= row_num <= max_rows + 1:
                    return row_num
                else:
                    print(f"❌ Please enter a valid row number between 2 and {max_rows + 1}")
            except ValueError:
                print("❌ Please enter a valid number")
    
    @staticmethod
    def display_row_info(row_num: int, row_data: dict):
        """Display information about the selected row"""
        print(f"\n📋 Row {row_num} Information:")
        print(f"   Name: {row_data.get('Name', 'N/A')}")
        print(f"   Company: {row_data.get('Company', 'N/A')}")
        print(f"   Email: {row_data.get('Email', 'N/A')}")
        print(f"   Status: {row_data.get('Read For Body?', 'N/A')}")
        
    @staticmethod
    def confirm_row_generation(row_num: int, name: str) -> bool:
        """Confirm generation for specific row"""
        response = input(f"🤔 Generate email for row {row_num} ({name})? (y/n): ").strip().lower()
        return response in ['y', 'yes']
