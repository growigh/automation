#!/usr/bin/env python3
"""
Google Sheets manager for email automation
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional, Tuple
from src.core.config import Config
from src.utils.email_utils import EmailUtils


class SheetsManager:
    """Manages Google Sheets operations"""
    
    def __init__(self):
        self.gc = None
        self.setup_google_sheets()
    
    def setup_google_sheets(self) -> bool:
        """Setup Google Sheets authentication"""
        try:
            service_account_file = Config.get_service_account_file()
            
            credentials = Credentials.from_service_account_file(
                service_account_file, scopes=Config.GOOGLE_SHEETS_SCOPE
            )
            self.gc = gspread.authorize(credentials)
            print("✅ Connected to Google Sheets")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Google Sheets: {e}")
            print(f"Make sure you have key.json file in your email-automation directory")
            print(f"Looking for: {Config.get_service_account_file()}")
            return False
    
    def is_connected(self) -> bool:
        """Check if Google Sheets is connected"""
        return self.gc is not None
    
    def get_spreadsheet_by_url(self, url: str):
        """Get spreadsheet by URL"""
        return self.gc.open_by_url(url.strip())
    
    def get_spreadsheet_by_id(self, sheet_id: str):
        """Get spreadsheet by ID"""
        return self.gc.open_by_key(sheet_id)
    
    def get_worksheet_records(self, worksheet) -> List[Dict]:
        """Get all records from a worksheet"""
        return worksheet.get_all_records()
    
    def get_column_mapping(self, worksheet) -> Dict[str, int]:
        """Get column name to index mapping"""
        header_row = worksheet.row_values(1)
        column_map = {}
        for i, header in enumerate(header_row, start=1):
            column_map[header] = i
        return column_map
    
    def validate_required_columns(self, column_map: Dict[str, int], required_columns: List[str]) -> Tuple[bool, List[str]]:
        """Validate if all required columns exist"""
        missing_columns = []
        for col in required_columns:
            if col not in column_map:
                missing_columns.append(col)
        return len(missing_columns) == 0, missing_columns
    
    def update_cell(self, worksheet, row: int, col: int, value: str) -> bool:
        """Update a single cell"""
        try:
            worksheet.update_cell(row, col, value)
            return True
        except Exception as e:
            print(f"❌ Error updating cell ({row}, {col}): {e}")
            return False
    
    def update_cell_by_column_letter(self, worksheet, row: int, col_letter: str, value: str) -> bool:
        """Update cell using column letter (e.g., A1, B2)"""
        try:
            worksheet.update(f"{col_letter}{row}", value)
            return True
        except Exception as e:
            print(f"❌ Error updating cell {col_letter}{row}: {e}")
            return False
    
    def find_sent_column(self, headers: List[str]) -> Optional[int]:
        """Find the 'sent' column index"""
        sent_column_names = ["sent?", "issent?", "is sent?", "issent", "sent"]
        
        for j, header in enumerate(headers, 1):
            if header.strip().lower() in sent_column_names:
                return j
        return None
    
    def mark_as_sent(self, worksheet, row_index: int, headers: List[str]) -> bool:
        """Mark email as sent in the worksheet"""
        try:
            sent_col_index = self.find_sent_column(headers)
            if sent_col_index:
                return self.update_cell(worksheet, row_index + 1, sent_col_index, "True")
            else:
                print("   ⚠️  No 'sent' column found to update")
                return False
        except Exception as e:
            print(f"❌ Error marking as sent: {e}")
            return False
    
    def process_sheets_from_urls(self, urls: List[str], processor_func) -> Tuple[int, int]:
        """Process multiple sheets from URLs"""
        total_processed = 0
        total_errors = 0
        
        for sheet_url in urls:
            if not sheet_url.strip():
                continue
            
            try:
                spreadsheet = self.get_spreadsheet_by_url(sheet_url)
                print(f"📊 Processing: {spreadsheet.title}")
                
                for worksheet in spreadsheet.worksheets():
                    processed, errors = processor_func(worksheet)
                    total_processed += processed
                    total_errors += errors
                    
            except Exception as e:
                print(f"❌ Error processing sheet {sheet_url}: {e}")
                total_errors += 1
        
        return total_processed, total_errors
