#!/usr/bin/env python3
"""
Google Sheets manager for email automation
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional, Tuple
from src.core.config import Config

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
    
    def check_cell_permissions(self, worksheet, row: int, col: int) -> bool:
        """Check if a cell can be edited (not protected)"""
        try:
            # Try to get the cell value first - if we can't even read it, there's a bigger issue
            current_value = worksheet.cell(row, col).value
            
            # Try to update with the same value to test permissions
            worksheet.update_cell(row, col, current_value or "")
            return True
        except Exception as e:
            error_msg = str(e)
            if "protected" in error_msg.lower() or "permission" in error_msg.lower():
                print(f"❌ Cell ({row}, {col}) is protected and cannot be edited")
                print(f"   Error: {error_msg}")
                return False
            else:
                print(f"❌ Unknown error checking cell ({row}, {col}): {error_msg}")
                return False

    def update_cell(self, worksheet, row: int, col: int, value: str) -> bool:
        """Update a single cell with permission checking"""
        # First check if we have permission to edit this cell
        if not self.check_cell_permissions(worksheet, row, col):
            print(f"❌ Cannot update cell ({row}, {col}) - insufficient permissions")
            print("   Please contact the spreadsheet owner to remove protection or grant edit access")
            return False
        
        try:
            worksheet.update_cell(row, col, value)
            return True
        except Exception as e:
            print(f"❌ Error updating cell ({row}, {col}): {e}")
            return False
    
    def find_sent_column(self, headers: List[str]) -> Optional[int]:
        """Find the 'sent' column index"""
        sent_column_names = ["sent?", "issent?", "is sent?", "issent", "sent"]
        
        for j, header in enumerate(headers, 1):
            if header.strip().lower() in sent_column_names:
                return j
                
        # Check for "SENT?" column specifically (case-sensitive)
        for j, header in enumerate(headers, 1):
            if header == "SENT?":
                return j
                
        return None
    
    def mark_as_sent(self, worksheet, row_index: int, headers: List[str]) -> bool:
        """Mark email as sent in the worksheet"""
        try:
            sent_col_index = self.find_sent_column(headers)
            if sent_col_index:
                # Check permissions before attempting update
                if not self.check_cell_permissions(worksheet, row_index + 1, sent_col_index):
                    print("❌ CRITICAL: Cannot update 'sent' status due to sheet protection")
                    print("   This will prevent proper tracking of sent emails")
                    print("   Please remove sheet protection or grant edit permissions")
                    print("   Stopping execution to prevent duplicate emails")
                    return False
                
                return self.update_cell(worksheet, row_index + 1, sent_col_index, "True")
            else:
                print("   ⚠️  No 'sent' column found to update")
                return False
        except Exception as e:
            print(f"❌ Error marking as sent: {e}")
            return False
    
    def check_sheet_permissions(self, worksheet) -> bool:
        """Check if we have edit permissions on the worksheet"""
        try:
            headers = worksheet.row_values(1)
            sent_col_index = self.find_sent_column(headers)
            
            if not sent_col_index:
                print("   ⚠️  No 'sent' column found - cannot track email status")
                return False
            
            # Test permissions on the first data row (row 2) if it exists
            if worksheet.row_count >= 2:
                print(f"   🔍 Checking permissions for 'sent' column (column {sent_col_index})...")
                if not self.check_cell_permissions(worksheet, 2, sent_col_index):
                    return False
                    
            print("   ✅ Sheet permissions verified")
            return True
            
        except Exception as e:
            print(f"❌ Error checking sheet permissions: {e}")
            return False
